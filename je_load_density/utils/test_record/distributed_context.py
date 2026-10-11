"""Explicit master aggregation composed of strict, independently owned worker contexts."""
from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from threading import RLock

from je_action_core.request_context import RunContext
from je_action_core.request_record import RequestRecord, RequestRecordError, validate_request_record


class DistributedRunContext:
    """Aggregate one run without weakening ActionCore's exact worker identity checks.

    Batch validation and global record-ID conflict checks complete before any child
    context is mutated. Child contexts remain private to the aggregate; snapshots
    share its lock and cannot observe a partially committed batch.
    """

    def __init__(self, source: str = "loaddensity", phase: str = "load", engine: str = "locust",
                 run_id: str | None = None) -> None:
        validated_identity = RunContext(source, phase, engine, run_id=run_id)
        self.run_id = validated_identity.run_id
        self.source, self.phase, self.engine = source, phase, engine
        self._workers: dict[str | None, RunContext] = {}
        self._index: dict[str, tuple[str | None, str]] = {}
        self._lock = RLock()

    def identity(self) -> dict[str, str]:
        """Return public wire identity, independently of Core's private storage."""
        return {"run_id": self.run_id, "source": self.source, "phase": self.phase, "engine": self.engine}

    def ingest_batch(self, worker_id: str, records: Sequence[Mapping[str, object]]) -> list[RequestRecord]:
        """Commit an entire authenticated-worker batch or reject it without mutation."""
        if not isinstance(worker_id, str) or not worker_id:
            raise RequestRecordError("worker_id: transport identity must be a non-empty string")
        return self._ingest(worker_id, records)

    def _ingest(self, worker_id: str | None, records: Sequence[Mapping[str, object]]) -> list[RequestRecord]:
        validated = [validate_request_record(record) for record in records]
        for record in validated:
            self._check_identity(worker_id, record)
        with self._lock:
            new_records = self._select_new(validated)
            staged = RunContext(self.source, self.phase, self.engine, worker_id=worker_id, run_id=self.run_id)
            for record in new_records:
                staged.append(record)
            current = self._workers.get(worker_id)
            if current is None:
                self._workers[worker_id] = staged
            else:
                for record in new_records:
                    current.append(record)
            for record in new_records:
                self._index[record["record_id"]] = (worker_id, self._fingerprint(record))
            return copy.deepcopy(new_records)

    def _check_identity(self, worker_id: str | None, record: RequestRecord) -> None:
        for field, expected in {**self.identity(), "worker_id": worker_id}.items():
            if record[field] != expected:
                raise RequestRecordError(f"{field}: does not belong to this distributed run or worker")

    def _select_new(self, records: list[RequestRecord]) -> list[RequestRecord]:
        staged = {}
        for record in records:
            identifier = record["record_id"]
            fingerprint = self._fingerprint(record)
            previous = self._index.get(identifier)
            if previous is not None:
                if previous[1] != fingerprint:
                    raise RequestRecordError("record_id: conflicting retry of an existing record")
                continue
            if identifier in staged and self._fingerprint(staged[identifier]) != fingerprint:
                raise RequestRecordError("record_id: conflicting records in one batch")
            staged[identifier] = record
        return list(staged.values())

    @staticmethod
    def _fingerprint(record: RequestRecord) -> str:
        return json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)

    def capture(self, fields: Mapping[str, object]) -> RequestRecord:
        """Capture an explicitly local master result while retaining the run-wide ID invariant."""
        local = RunContext(self.source, self.phase, self.engine, run_id=self.run_id)
        record = local.capture(fields)
        self._ingest(None, [record])
        return record

    def snapshot(self) -> list[RequestRecord]:
        """Return a detached insertion-ordered snapshot across source workers."""
        with self._lock:
            records = {record["record_id"]: record for context in self._workers.values()
                       for record in context.snapshot()}
            return [records[identifier] for identifier in self._index]

    def to_json(self) -> str:
        """Export validated canonical records without changing worker provenance."""
        return json.dumps(self.snapshot(), ensure_ascii=False, allow_nan=False)
