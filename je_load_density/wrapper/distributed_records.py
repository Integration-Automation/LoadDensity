"""Opt-in bounded canonical result delivery over Locust's native message channel."""
from __future__ import annotations

import copy
import json
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from time import monotonic
from uuid import uuid4

import gevent
from je_action_core.request_record import validate_request_record
from locust.exception import RPCError

from je_load_density.utils.test_record.contract import from_legacy_record
from je_load_density.utils.test_record.distributed_context import DistributedRunContext
from je_load_density.utils.test_record.test_record_class import test_record_instance

HELLO = "ld_records_hello_v1"
CONFIG = "ld_records_config_v1"
READY = "ld_records_ready_v1"
BATCH = "ld_records_batch_v1"
ACK = "ld_records_ack_v1"
FLUSH = "ld_records_flush_v1"
DONE = "ld_records_done_v1"
FINISHED = "ld_records_finished_v1"
MAX_CONTROL_NONCE_BYTES = 128
RETIRED_EPOCH_LIMIT = 128
TERMINAL_FIELDS = frozenset(("protocol", "run_id", "worker_id", "epoch", "generation", "nonce", "pending"))


class RecordDeliveryError(RuntimeError):
    """Canonical delivery is incomplete or violates its negotiated contract."""


def _encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _message_fits(data: dict, byte_limit: int) -> bool:
    try:
        return len(_encoded(data)) <= byte_limit
    except (TypeError, ValueError):
        return False


def _control_valid(data, limits: DeliveryLimits, fields: frozenset[str]) -> bool:
    if not isinstance(data, dict) or set(data) != fields:
        return False
    nonce = data.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        return False
    try:
        return len(nonce.encode("utf-8")) <= MAX_CONTROL_NONCE_BYTES and len(_encoded(data)) <= limits.max_batch_bytes
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class DeliveryLimits:
    """Bound every buffered queue and serialized batch; retry interval also flushes new work."""

    batch_size: int = 100
    max_batch_bytes: int = 262144
    max_record_bytes: int = 65536
    max_pending: int = 1000
    max_pending_bytes: int = 4194304
    interval: float = 0.1
    drain_timeout: float = 2.0

    def __post_init__(self) -> None:
        integers = (self.batch_size, self.max_batch_bytes, self.max_record_bytes,
                    self.max_pending, self.max_pending_bytes)
        if any(type(value) is not int or value <= 0 for value in integers):
            raise ValueError("record count and byte limits must be positive integers")
        times = (self.interval, self.drain_timeout)
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in times):
            raise ValueError("record delivery intervals must be positive finite numbers")
        if self.max_record_bytes >= self.max_batch_bytes or self.max_pending_bytes < self.max_record_bytes:
            raise ValueError("record limits must fit within batch and pending byte limits")

    @classmethod
    def from_options(cls, options: dict) -> DeliveryLimits:
        """Read explicit bounds through the wrapper's existing keyword interface."""
        names = ("record_batch_size", "record_batch_bytes", "record_max_bytes", "record_max_pending",
                 "record_pending_bytes", "record_flush_interval", "record_drain_timeout")
        defaults = cls()
        values = (getattr(defaults, field) for field in cls.__dataclass_fields__)
        return cls(*(options.get(name, default) for name, default in zip(names, values)))


class _Delivery:
    def __init__(self, environment, limits: DeliveryLimits) -> None:
        self.environment = environment
        self.limits = limits
        self.error: RecordDeliveryError | None = None
        self.closed = False
        self.send_failures = 0
        self._listeners = []
        self._drain_owner = None

    def _listen(self, hook, callback) -> None:
        hook.add_listener(callback)
        self._listeners.append((hook, callback))

    def _send(self, kind: str, data: dict, worker_id: str | None = None) -> bool:
        if not _message_fits(data, self.limits.max_batch_bytes):
            self.send_failures += 1
            self._fail("canonical outgoing message exceeds byte limit or is not serializable")
            return False
        try:
            with gevent.Timeout(min(self.limits.interval, self.limits.drain_timeout), False):
                self.environment.runner.send_message(kind, copy.deepcopy(data), client_id=worker_id)
                return True
        except RPCError:
            self.send_failures += 1
            return False
        self.send_failures += 1
        return False

    def _fail(self, message: str, stop: bool = True) -> RecordDeliveryError:
        if self.error is None:
            self.error = RecordDeliveryError(message)
            self.environment.process_exit_code = 1
            if self.environment.cancellation_error is None:
                self.environment.cancellation_error = self.error
            health = getattr(self.environment, "distributed_health", None)
            if health is not None:
                health.fail(message)
            if stop:
                self.environment.load_density_tasks.spawn(self.environment.runner.quit)
        return self.error

    def raise_if_failed(self) -> None:
        """Surface a delivery failure after the owning wrapper completes resource cleanup."""
        if self.error is not None:
            raise self.error

    def _detach(self) -> None:
        for hook, callback in self._listeners:
            hook.remove_listener(callback)

    def _begin_close(self) -> bool:
        if self.closed or self._drain_owner is gevent.getcurrent():
            return False
        if self._drain_owner is not None:
            while not self.closed:
                gevent.sleep(self.limits.interval)
            return False
        self._drain_owner = gevent.getcurrent()
        return True


class WorkerRecords(_Delivery):
    """One bounded producer epoch; retry an identical in-flight batch until acknowledged."""

    role = "worker"

    def __init__(self, environment, limits: DeliveryLimits) -> None:
        super().__init__(environment, limits)
        self.epoch = str(uuid4())
        self.worker_id = environment.runner.client_id
        self.identity = None
        self.generation = 0
        self.pending = deque()
        self.pending_bytes = 0
        self.frame = None
        self.seq = 1
        self.delivered = 0
        self.finalized = False
        self._final_nonce = None
        environment.runner.register_message(CONFIG, self.on_config)
        environment.runner.register_message(ACK, self.on_ack)
        environment.runner.register_message(FLUSH, self._on_flush)
        environment.runner.register_message(FINISHED, self._on_finished)
        self._listen(environment.events.test_stop, self._on_stop)

    def _base(self) -> dict:
        return {"protocol": 1, "epoch": self.epoch, "worker_id": self.worker_id,
                "generation": self.generation, "run_id": self.identity["run_id"] if self.identity else None}

    def on_config(self, msg, **_kwargs) -> None:
        """Bind only this producer epoch to a validated master run identity."""
        if self.closed or not isinstance(msg.data, dict):
            return
        data = msg.data
        if data.get("epoch") != self.epoch or data.get("worker_id") != self.worker_id:
            return
        try:
            identity = {field: data[field] for field in ("run_id", "source", "phase", "engine")}
            generation = data["generation"]
            if type(data.get("protocol")) is not int or data["protocol"] != 1:
                raise ValueError("invalid record handshake protocol")
            if type(generation) is not int or generation <= 0:
                raise ValueError("invalid record handshake generation")
            if generation < self.generation:
                return
            from je_action_core.request_context import RunContext
            RunContext(**identity, worker_id=self.worker_id)
            if identity["engine"] != "locust":
                raise ValueError("record handshake engine must be locust")
            self._negotiate(data.get("limits"))
            self._bind(identity, generation)
        except (KeyError, TypeError, ValueError) as error:
            self._fail(f"invalid canonical record handshake: {error}")

    def _negotiate(self, remote: dict | None) -> None:
        if remote is None:
            return
        negotiated = DeliveryLimits(**remote)
        local = asdict(self.limits)
        self.limits = DeliveryLimits(**{key: min(value, getattr(negotiated, key)) for key, value in local.items()})
        if len(self.pending) > self.limits.max_pending or self.pending_bytes > self.limits.max_pending_bytes:
            raise ValueError("pending records exceed negotiated limits")

    def _bind(self, identity: dict, generation: int) -> None:
        if self.identity is not None and identity != self.identity and self.pending:
            raise ValueError("master run changed with pending records")
        if self.identity is not None and generation < self.generation:
            return
        if identity == self.identity and generation == self.generation:
            self._send(READY, self._base())
            return
        if self.identity is None:
            rebound = [validate_request_record({**record, **identity}) for record, _size in self.pending]
            sizes = [len(_encoded(record)) for record in rebound]
            if any(size > self.limits.max_record_bytes for size in sizes):
                raise ValueError("record exceeds negotiated record byte limit")
            if sum(sizes) > self.limits.max_pending_bytes:
                raise ValueError("pending records exceed negotiated byte limit")
            self.pending = deque(zip(rebound, sizes))
            self.pending_bytes = sum(sizes)
        self.identity = identity
        self.generation = generation
        self.frame = None
        self.seq = 1
        self._send(READY, self._base())

    def capture_legacy(self, entry: dict, outcome: str) -> None:
        """Capture measurements into the bounded producer instead of an unbounded worker history."""
        from_legacy_record(entry, self, outcome)

    def capture(self, fields) -> dict:
        """Assign a UUID once; preserve it across batching, retries and reconnection."""
        if self.closed or self.error is not None:
            raise self._fail("canonical record producer is closed or failed", stop=False)
        identity = self.identity or {"run_id": "awaiting-master", "source": "loaddensity",
                                     "phase": "load", "engine": "locust"}
        record = validate_request_record({"schema_version": 1, "record_id": str(uuid4()),
            "scenario_id": None, "step_id": None, "assertions": [], "extensions": {}, **fields,
            **identity, "worker_id": self.worker_id})
        size = len(_encoded(record))
        if size > self.limits.max_record_bytes:
            raise self._fail("canonical record exceeds record byte limit")
        if len(self.pending) >= self.limits.max_pending or self.pending_bytes + size > self.limits.max_pending_bytes:
            raise self._fail("canonical pending queue exceeds count or byte limit")
        self.pending.append((record, size))
        self.pending_bytes += size
        self.finalized = False
        return copy.deepcopy(record)

    def _batch(self) -> dict:
        records = []
        frame = {**self._base(), "seq": self.seq, "records": records, "byte_count": 0}
        for record, _size in self.pending:
            if len(records) >= self.limits.batch_size:
                break
            records.append(record)
            frame["byte_count"] = len(_encoded(records))
            if len(_encoded(frame)) > self.limits.max_batch_bytes:
                records.pop()
                frame["byte_count"] = len(_encoded(records))
                break
        if not records:
            raise self._fail("record cannot fit within the canonical batch byte limit")
        return frame

    def flush(self) -> None:
        """Attempt delivery without discarding unacknowledged records on transport errors."""
        if self.closed or self.error is not None or self.identity is None or not self.pending:
            return
        if self.frame is None:
            self.frame = self._batch()
        self._send(BATCH, self.frame)

    def on_ack(self, msg, **_kwargs) -> None:
        """Only a matching run/epoch/generation/sequence may release the in-flight queue prefix."""
        if self.closed or self.frame is None or not isinstance(msg.data, dict):
            return
        data = msg.data
        if type(data.get("generation")) is not int or type(data.get("seq")) is not int:
            return
        if any(data.get(field) != self.frame[field] for field in
               ("run_id", "worker_id", "epoch", "generation", "seq")):
            return
        if data.get("ok") is not True:
            self._fail("master rejected canonical batch: " + str(data.get("error", "unknown error")))
            return
        count = len(self.frame["records"])
        for _ in range(count):
            _record, size = self.pending.popleft()
            self.pending_bytes -= size
        self.delivered += count
        self.frame = None
        self.seq += 1

    def run(self) -> None:
        """Retry handshake/delivery on the native connection; the owner controls this task's lifetime."""
        next_hello = 0.0
        while not self.closed and self.error is None:
            if self.identity is None or monotonic() >= next_hello:
                self._send(HELLO, self._base())
                next_hello = monotonic() + 1.0
            self.flush()
            gevent.sleep(self.limits.interval)

    def _on_stop(self, **_kwargs) -> None:
        self.flush()

    def _on_flush(self, msg, **_kwargs) -> None:
        if self.identity is None or not _control_valid(msg.data, self.limits, frozenset(("run_id", "nonce"))):
            return
        if msg.data.get("run_id") == self.identity["run_id"]:
            self.environment.load_density_tasks.spawn(self._drain_done, msg.data.get("nonce"))

    def _drain(self) -> None:
        deadline = monotonic() + self.limits.drain_timeout
        while self.pending and self.error is None and monotonic() < deadline:
            self.flush()
            gevent.sleep(self.limits.interval)

    def _drain_done(self, nonce) -> None:
        self.environment.runner.stop()
        self._drain()
        self._send_done(nonce)

    def _send_done(self, nonce) -> None:
        self._final_nonce = nonce
        self._send(DONE, {**self._base(), "nonce": nonce, "pending": len(self.pending)})

    def _on_finished(self, msg, **_kwargs) -> None:
        data = msg.data
        if self.identity is None or self.pending or not _control_valid(data, self.limits, TERMINAL_FIELDS):
            return
        if type(data.get("protocol")) is not int or type(data.get("generation")) is not int:
            return
        if type(data.get("pending")) is not int or data["pending"] != 0:
            return
        if all(data.get(key) == value for key, value in self._base().items()):
            self.finalized = data.get("nonce") == self._final_nonce

    def _finish_delivery(self) -> None:
        if self.identity is None or self.finalized or self.error is not None:
            return
        nonce = str(uuid4())
        deadline = monotonic() + self.limits.drain_timeout
        while not self.finalized and monotonic() < deadline:
            self._send_done(nonce)
            gevent.sleep(self.limits.interval)
        if not self.finalized:
            self._fail("canonical final delivery acknowledgement was not received", stop=False)

    def close(self) -> None:
        """Bound the final drain and retain exact pending-loss diagnostics on failure."""
        if not self._begin_close():
            return
        try:
            self.environment.runner.stop()
            self._drain()
            if self.pending:
                self._fail(f"canonical delivery incomplete: {len(self.pending)} unacknowledged records", stop=False)
            self._finish_delivery()
        finally:
            self.closed = True
            self._detach()

    def snapshot(self) -> dict:
        """Return bounded queue and delivery diagnostics; counts never imply HTTP exactly-once execution."""
        return {"role": self.role, "ready": self.identity is not None, "generation": self.generation,
                "pending_records": len(self.pending), "pending_bytes": self.pending_bytes,
                "delivered_records": self.delivered, "send_failures": self.send_failures,
                "error": str(self.error) if self.error else None}


@dataclass
class _Session:
    epoch: str
    generation: int
    ready: bool = False
    seq: int = 0
    fingerprint: bytes | None = None
    finished: bool = False
    retired_epochs: set[str] = field(default_factory=set)


class MasterRecords(_Delivery):
    """Validate transport provenance, atomically aggregate records, and acknowledge accepted batches."""

    role = "master"

    def __init__(self, environment, context: DistributedRunContext, limits: DeliveryLimits) -> None:
        super().__init__(environment, limits)
        if context.engine != "locust":
            raise ValueError("distributed record aggregation requires engine=locust")
        self.context = context
        self.sessions: dict[str, _Session] = {}
        self.accepted = 0
        self.duplicates = 0
        self.rejected = 0
        self.incomplete_workers = set()
        self._nonce = None
        self._awaiting = set()
        environment.runner.register_message(HELLO, self.on_hello)
        environment.runner.register_message(READY, self._on_ready)
        environment.runner.register_message(BATCH, self.on_batch)
        environment.runner.register_message(DONE, self._on_done)
        self._listen(environment.events.test_stopping, self._on_stopping)

    @property
    def ready_count(self) -> int:
        """Count canonical-ready workers only when their native readiness and heartbeat are healthy."""
        return sum(client.state == "ready" and client.heartbeat >= 0 and
                   self.sessions.get(client.id) is not None and self.sessions[client.id].ready
                   for client in self.environment.runner.clients.all)

    def on_hello(self, msg, **_kwargs) -> None:
        """Negotiate a run-bound generation for a known native worker and producer epoch."""
        if self.closed:
            return
        try:
            data = msg.data
            worker_id = msg.node_id
            self._validate_hello(worker_id, data)
            session = self._negotiate_session(worker_id, data)
            if session is None:
                return
            self.sessions[worker_id] = session
            self._send(CONFIG, {**self.context.identity(), "protocol": 1, "worker_id": worker_id,
                       "epoch": session.epoch, "generation": session.generation,
                       "limits": asdict(self.limits)}, worker_id)
        except (KeyError, TypeError, ValueError, RecordDeliveryError) as error:
            self.rejected += 1
            self._fail(f"canonical worker handshake rejected: {error}")

    def _negotiate_session(self, worker_id: str, data: dict) -> _Session | None:
        current = self.sessions.get(worker_id)
        if current is None:
            return _Session(data["epoch"], 1)
        if current.epoch == data["epoch"]:
            return current
        if data["epoch"] in current.retired_epochs:
            self.rejected += 1
            return None
        if type(data.get("generation")) is not int or data["generation"] != 0:
            raise RecordDeliveryError("stale producer epoch")
        if len(current.retired_epochs) >= RETIRED_EPOCH_LIMIT:
            raise RecordDeliveryError("retired producer epoch history capacity reached")
        return _Session(data["epoch"], current.generation + 1,
                        retired_epochs=current.retired_epochs | {current.epoch})

    def _validate_hello(self, worker_id: str, data) -> None:
        if not isinstance(data, dict) or type(data.get("protocol")) is not int or data["protocol"] != 1:
            raise RecordDeliveryError("invalid canonical handshake protocol")
        if data.get("worker_id") != worker_id or worker_id not in self.environment.runner.clients:
            raise RecordDeliveryError("worker_id: handshake transport identity mismatch")
        if not isinstance(data.get("epoch"), str) or not data["epoch"] or len(data["epoch"]) > 128:
            raise RecordDeliveryError("invalid producer epoch")
        if len(_encoded(data)) > self.limits.max_batch_bytes:
            raise RecordDeliveryError("handshake exceeds byte limit")

    def _session(self, worker_id: str, data: dict) -> _Session:
        if not isinstance(data, dict) or type(data.get("protocol")) is not int or data["protocol"] != 1:
            raise RecordDeliveryError("invalid canonical message protocol")
        session = self.sessions.get(worker_id)
        if data.get("run_id") != self.context.run_id:
            raise RecordDeliveryError("run_id: foreign canonical batch")
        if data.get("worker_id") != worker_id or session is None:
            raise RecordDeliveryError("worker_id: batch transport identity mismatch")
        if type(data.get("generation")) is not int:
            raise RecordDeliveryError("invalid canonical producer generation")
        if data.get("epoch") != session.epoch or data.get("generation") != session.generation:
            raise RecordDeliveryError("stale canonical producer generation")
        return session

    def _on_ready(self, msg, **_kwargs) -> None:
        try:
            self._session(msg.node_id, msg.data).ready = True
        except (AttributeError, TypeError, RecordDeliveryError):
            self.rejected += 1

    def on_batch(self, msg, **_kwargs) -> None:
        """Reject malformed/foreign batches before mutation; acknowledge identical retries once."""
        if self.closed:
            return
        data = msg.data
        try:
            session = self._validate_batch(msg.node_id, data)
            fingerprint = _encoded(data)
            if data["seq"] == session.seq:
                if fingerprint != session.fingerprint:
                    raise RecordDeliveryError("conflicting retry of canonical batch")
                self.duplicates += 1
                accepted = []
            else:
                accepted = self.context.ingest_batch(msg.node_id, data["records"])
                for record in accepted:
                    _append_legacy(record)
                self.accepted += len(accepted)
                session.seq = data["seq"]
                session.fingerprint = fingerprint
                session.finished = False
            self._ack(msg.node_id, data, True, len(accepted))
        except (KeyError, TypeError, ValueError, RecordDeliveryError) as error:
            self.rejected += 1
            self._ack(msg.node_id, data if isinstance(data, dict) else {}, False, 0, str(error))
            self._fail(f"canonical batch rejected: {error}")

    def _validate_batch(self, worker_id: str, data: dict) -> _Session:
        session = self._session(worker_id, data)
        if type(data.get("seq")) is not int or data["seq"] not in (session.seq, session.seq + 1):
            raise RecordDeliveryError("unexpected canonical batch sequence")
        if data["seq"] <= 0:
            raise RecordDeliveryError("invalid canonical batch sequence")
        self._validate_records(data)
        return session

    def _validate_records(self, data: dict) -> None:
        records = data.get("records")
        if not isinstance(records, list) or not records or len(records) > self.limits.batch_size:
            raise RecordDeliveryError("canonical batch record count exceeds limit")
        if len(_encoded(data)) > self.limits.max_batch_bytes:
            raise RecordDeliveryError("canonical batch byte limit exceeded")
        if type(data.get("byte_count")) is not int or data["byte_count"] != len(_encoded(records)):
            raise RecordDeliveryError("canonical batch byte_count mismatch")
        if any(len(_encoded(record)) > self.limits.max_record_bytes for record in records):
            raise RecordDeliveryError("canonical record byte limit exceeded")

    def _ack(self, worker_id: str, data: dict, ok: bool, count: int, error: str | None = None) -> None:
        base = {field: data.get(field) for field in ("run_id", "worker_id", "epoch", "generation", "seq")}
        self._send(ACK, {**base, "ok": ok, "accepted": count, "error": error}, worker_id)

    def _on_done(self, msg, **_kwargs) -> None:
        if not _control_valid(msg.data, self.limits, TERMINAL_FIELDS):
            self.rejected += 1
            return
        try:
            session = self._session(msg.node_id, msg.data)
            if type(msg.data.get("pending")) is not int or not 0 <= msg.data["pending"] <= self.limits.max_pending:
                return
            session.finished = msg.data["pending"] == 0
            if session.finished:
                response = {key: msg.data[key] for key in TERMINAL_FIELDS}
                self._send(FINISHED, response, msg.node_id)
            if msg.data.get("nonce") == self._nonce and session.finished:
                self._awaiting.discard(msg.node_id)
        except (AttributeError, TypeError, RecordDeliveryError):
            self.rejected += 1

    def _on_stopping(self, **_kwargs) -> None:
        self.close()

    def _freeze_health(self) -> None:
        health = getattr(self.environment, "distributed_health", None)
        if health is not None and not getattr(self.environment, "record_health_closed", False):
            health.close()
            self.environment.record_health_closed = True

    def close(self) -> None:
        """Ask live producers for a final drain while the native RPC listener can still acknowledge."""
        if not self._begin_close():
            return
        self._freeze_health()
        try:
            self._drain_workers()
        finally:
            self.closed = True
            self._detach()

    def _drain_workers(self) -> None:
        self._nonce = str(uuid4())
        clients = self.environment.runner.clients
        for worker_id, session in self.sessions.items():
            if session.finished:
                continue
            if worker_id not in clients or clients[worker_id].state == "missing":
                self.incomplete_workers.add(worker_id)
            else:
                self._awaiting.add(worker_id)
        self.incomplete_workers.update(set(clients) - set(self.sessions))
        for worker_id in self._awaiting.copy():
            self._send(FLUSH, {"run_id": self.context.run_id, "nonce": self._nonce}, worker_id)
        deadline = monotonic() + self.limits.drain_timeout
        while self._awaiting and monotonic() < deadline:
            gevent.sleep(self.limits.interval)
        self.incomplete_workers.update(self._awaiting)
        if self.incomplete_workers:
            self._fail("canonical delivery incomplete for workers: " + ", ".join(sorted(self.incomplete_workers)),
                       stop=False)

    def snapshot(self) -> dict:
        """Expose aggregate delivery separately from native worker capacity health."""
        return {"role": self.role, "run_id": self.context.run_id, "accepted_records": self.accepted,
                "duplicate_batches": self.duplicates, "rejected_batches": self.rejected,
                "incomplete_workers": sorted(self.incomplete_workers), "send_failures": self.send_failures,
                "error": str(self.error) if self.error else None}


def _append_legacy(record: dict) -> None:
    successful = record["outcome"] == "passed"
    entry = {"Method": record["request_method"], "test_url": record["request_url"], "name": record["name"],
             "status_code": str(record["status_code"]) if record["status_code"] is not None else None,
             "text": record.get("text"), "response_time_ms": record["response_time_ms"],
             "response_length": record["response_length"], "start_time": record["start_time"],
             "error": None if successful else record["error"]["message"],
             "run_id": record["run_id"], "worker_id": record["worker_id"], "record_id": record["record_id"]}
    if successful:
        entry.update(content=record.get("content_base64"), headers=record.get("headers"))
    records = test_record_instance.test_record_list if successful else test_record_instance.error_record_list
    records.append(entry)


def delivery_options(mode: str, context, enabled: bool, options: dict):
    """Validate opt-in delivery before allocating a native runner or RPC transport."""
    if enabled:
        if mode != "worker" or context is not None:
            raise ValueError("distributed_records is only for workers receiving identity from their master")
        return ("worker", None, DeliveryLimits.from_options(options))
    if not isinstance(context, DistributedRunContext):
        return None
    if mode != "master" or context.engine != "locust":
        raise ValueError("DistributedRunContext requires a native Locust master with engine=locust")
    return ("master", context, DeliveryLimits.from_options(options))


def attach_delivery(environment, options: tuple) -> None:
    """Attach native message handlers and owned producer tasks after runner creation."""
    role, context, limits = options
    if role == "master":
        environment.record_delivery = MasterRecords(environment, context, limits)
        environment.record_run_context = context
        return
    from functools import partial

    from je_load_density.wrapper.event.request_hook import request_hook
    producer = WorkerRecords(environment, limits)
    environment.record_delivery = producer
    producer._listen(environment.events.request, partial(request_hook, record_sink=producer))
    environment.load_density_tasks.spawn(producer.run)
