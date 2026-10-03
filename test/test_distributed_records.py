"""Canonical aggregation and native worker delivery contracts."""
import importlib
import json

import pytest

pytest.importorskip("je_action_core.request_context", reason="canonical records require the new ActionCore API")

from je_load_density.utils.test_record.run_context import RunContext  # noqa: E402


def delivery_module():
    spec = importlib.util.find_spec("je_load_density.wrapper.distributed_records")
    assert spec is not None, "distributed delivery is not implemented"
    return importlib.import_module("je_load_density.wrapper.distributed_records")


def fake_environment(worker_id="worker-a"):
    from types import SimpleNamespace

    from gevent.pool import Group
    from locust.event import Events

    sent = []
    handlers = {}
    runner = SimpleNamespace(client_id=worker_id, clients={},
                             register_message=lambda name, handler: handlers.update({name: handler}),
                             send_message=lambda name, data=None, client_id=None: sent.append((name, data, client_id)),
                             quit=lambda: None, stop=lambda: None)
    env = SimpleNamespace(runner=runner, events=Events(), load_density_tasks=Group(),
                          cancellation_error=None, process_exit_code=None)
    return env, sent, handlers


def configure(producer, generation=1):
    from types import SimpleNamespace
    producer.on_config(msg=SimpleNamespace(data={"protocol": 1, "run_id": "run-one", "source": "loaddensity",
        "phase": "load", "engine": "locust", "worker_id": "worker-a", "generation": generation,
        "epoch": producer.epoch}))


def legacy_entry():
    return {"Method": "GET", "test_url": "http://localhost/", "name": "home", "status_code": "200",
            "response_time_ms": 25, "response_length": 2, "start_time": 100.0}


def aggregate():
    spec = importlib.util.find_spec("je_load_density.utils.test_record.distributed_context")
    assert spec is not None, "distributed aggregate is not implemented"
    module = importlib.import_module("je_load_density.utils.test_record.distributed_context")
    return module.DistributedRunContext(run_id="run-one")


def measured(worker="worker-a", identifier="record-one", **overrides):
    context = RunContext("loaddensity", "load", "locust", worker_id=worker, run_id="run-one")
    return context.capture({"record_id": identifier, "protocol": "http", "request_method": "GET",
                            "request_url": "http://localhost/", "name": "home", "status_code": 200,
                            "start_time": 100.0, "end_time": 100.025, "response_time_ms": 25,
                            "response_length": 2, "outcome": "passed", "error": None, **overrides})


def test_aggregate_preserves_workers_and_globally_deduplicates_retries():
    run = aggregate()
    first = measured()
    second = measured("worker-b", "record-two")
    assert len(run.ingest_batch("worker-a", [first])) == 1
    assert run.ingest_batch("worker-a", [dict(reversed(list(first.items())))]) == []
    assert len(run.ingest_batch("worker-b", [second])) == 1
    assert [item["worker_id"] for item in run.snapshot()] == ["worker-a", "worker-b"]
    assert [item["record_id"] for item in json.loads(run.to_json())] == ["record-one", "record-two"]


@pytest.mark.parametrize("field,value", [("run_id", "foreign"), ("engine", "asyncio"),
                                         ("source", "apitestka"), ("phase", "functional"),
                                         ("worker_id", "worker-b")])
def test_foreign_identity_rejects_whole_batch(field, value):
    run = aggregate()
    bad = measured(identifier="record-two")
    bad[field] = value
    with pytest.raises(ValueError, match=field):
        run.ingest_batch("worker-a", [measured(), bad])
    assert run.snapshot() == []


def test_conflicting_retry_rejects_new_records_in_same_batch():
    run = aggregate()
    original = measured()
    run.ingest_batch("worker-a", [original])
    conflicting = measured(response_time_ms=25.0)
    with pytest.raises(ValueError, match="conflicting"):
        run.ingest_batch("worker-a", [measured(identifier="record-new"), conflicting])
    assert run.snapshot() == [original]


def test_record_identifier_cannot_be_reused_by_another_worker():
    run = aggregate()
    run.ingest_batch("worker-a", [measured()])
    with pytest.raises(ValueError, match="record_id"):
        run.ingest_batch("worker-b", [measured("worker-b")])
    assert len(run.snapshot()) == 1


def test_malformed_record_rejects_entire_batch():
    run = aggregate()
    malformed = measured(identifier="record-two")
    malformed["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version"):
        run.ingest_batch("worker-a", [measured(), malformed])
    assert run.snapshot() == []


def test_aggregate_snapshot_is_detached():
    run = aggregate()
    run.ingest_batch("worker-a", [measured()])
    snapshot = run.snapshot()
    snapshot[0]["name"] = "changed"
    assert run.snapshot()[0]["name"] == "home"


def test_producer_retries_identical_bounded_batch_until_matching_ack():
    module = delivery_module()
    env, sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(batch_size=2))
    configure(producer)
    for _ in range(3):
        producer.capture_legacy(legacy_entry(), "passed")
    producer.flush()
    first = sent[-1][1]
    producer.flush()
    assert sent[-1][1] == first
    assert len(first["records"]) == 2
    assert len({record["record_id"] for record in first["records"]}) == 2
    producer.on_ack(msg=type("Message", (), {"data": {**first, "ok": True, "records": None}})())
    producer.flush()
    assert sent[-1][1]["seq"] == 2
    assert len(sent[-1][1]["records"]) == 1
    assert producer.snapshot()["pending_records"] == 1


def test_stale_ack_cannot_release_pending_records():
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    producer.flush()
    producer.on_ack(msg=type("Message", (), {"data": {"run_id": "run-one", "worker_id": "worker-a",
        "epoch": producer.epoch, "generation": 0, "seq": 1, "ok": True}})())
    assert producer.snapshot()["pending_records"] == 1


def test_pending_overflow_fails_without_unbounded_queue_growth():
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(max_pending=2))
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    producer.capture_legacy(legacy_entry(), "passed")
    with pytest.raises(module.RecordDeliveryError, match="pending"):
        producer.capture_legacy(legacy_entry(), "passed")
    assert producer.snapshot()["pending_records"] == 2
    assert env.process_exit_code == 1
    env.load_density_tasks.kill()


def test_record_byte_limit_rejects_oversized_record_before_enqueuing():
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(max_record_bytes=1024))
    configure(producer)
    oversized = {**legacy_entry(), "name": "x" * 2000}
    with pytest.raises(module.RecordDeliveryError, match="record"):
        producer.capture_legacy(oversized, "passed")
    assert producer.snapshot()["pending_records"] == 0
    env.load_density_tasks.kill()


def frame(records, **overrides):
    size = len(json.dumps(records, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode("utf-8"))
    return {"protocol": 1, "run_id": "run-one", "worker_id": "worker-a", "epoch": "producer-a",
            "generation": 1, "seq": 1, "records": records, "byte_count": size, **overrides}


def receiver():
    from types import SimpleNamespace
    module = delivery_module()
    assert hasattr(module, "MasterRecords"), "master record receiver is not implemented"
    env, sent, handlers = fake_environment()
    env.runner.clients["worker-a"] = SimpleNamespace(state="ready", heartbeat=1)
    run = aggregate()
    bridge = module.MasterRecords(env, run, module.DeliveryLimits())
    bridge.on_hello(msg=SimpleNamespace(node_id="worker-a", data={"protocol": 1, "epoch": "producer-a",
                       "worker_id": "worker-a", "generation": 0, "run_id": None}))
    return bridge, run, env, sent, handlers


def test_master_retries_ack_without_duplicating_canonical_or_legacy_results():
    from types import SimpleNamespace

    from je_load_density.utils.test_record.test_record_class import test_record_instance
    test_record_instance.clear_records()
    bridge, run, _env, sent, _ = receiver()
    message = SimpleNamespace(node_id="worker-a", data=frame([measured()]))
    bridge.on_batch(msg=message)
    bridge.on_batch(msg=message)
    assert len(run.snapshot()) == 1
    assert len(test_record_instance.test_record_list) == 1
    assert sent[-1][1]["ok"] is True
    assert bridge.snapshot()["duplicate_batches"] == 1
    assert test_record_instance.test_record_list[0]["worker_id"] == "worker-a"
    test_record_instance.clear_records()


@pytest.mark.parametrize("overrides", [{"worker_id": "spoofed"}, {"generation": 0}, {"seq": 2},
                                     {"run_id": "foreign"}, {"byte_count": 1}])
def test_master_invalid_envelope_cannot_partially_ingest(overrides):
    from types import SimpleNamespace
    bridge, run, env, sent, _ = receiver()
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()], **overrides)))
    assert run.snapshot() == []
    assert sent[-1][1]["ok"] is False
    assert env.process_exit_code == 1
    env.load_density_tasks.kill()


def test_same_generation_handshake_does_not_change_inflight_batch():
    module = delivery_module()
    env, sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    producer.flush()
    original = sent[-1][1]
    producer.capture_legacy(legacy_entry(), "passed")
    configure(producer)
    producer.flush()
    assert sent[-1][1] == original


def until(predicate, timeout=5):
    import gevent
    with gevent.Timeout(timeout):
        while not predicate():
            gevent.sleep(0.005)


@pytest.fixture
def native_pair():
    import gevent
    from locust import User, task

    from je_load_density.utils.test_record.test_record_class import test_record_instance
    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper

    class IdleUser(User):
        @task
        def idle(self):
            gevent.sleep(0.01)

    test_record_instance.clear_records()
    run = aggregate()
    master = wrapper.create_env(IdleUser, runner_mode="master", master_bind_host="127.0.0.1",
                                master_bind_port=0, run_context=run, record_flush_interval=0.01,
                                record_drain_timeout=2)
    worker = None
    try:
        worker = wrapper.create_env(IdleUser, runner_mode="worker", master_host="127.0.0.1",
                                    master_port=master.runner.server.port, distributed_records=True,
                                    record_flush_interval=0.01, record_drain_timeout=2)
        until(lambda: master.record_delivery.ready_count == 1)
        yield master, worker, run
    finally:
        wrapper.cleanup_env(master)
        if worker is not None:
            wrapper.cleanup_env(worker)
        test_record_instance.clear_records()


def fire_request(env, *, exception=None):
    env.events.request.fire(start_time=100, url="http://localhost/", request_type="GET", name="home",
                            context={}, response=None, exception=exception, response_length=2, response_time=25)


def test_native_rpc_binds_identity_and_aggregates_worker_request_hook(native_pair):
    from je_load_density.utils.test_record.test_record_class import test_record_instance
    master, worker, run = native_pair
    fire_request(worker)
    fire_request(worker, exception=ValueError("HTTP failed"))
    until(lambda: len(run.snapshot()) == 2 and worker.record_delivery.snapshot()["pending_records"] == 0)
    assert {item["worker_id"] for item in run.snapshot()} == {worker.runner.client_id}
    assert {item["run_id"] for item in run.snapshot()} == {run.run_id}
    assert len(test_record_instance.test_record_list) == 1
    assert len(test_record_instance.error_record_list) == 1
    assert master.record_delivery.snapshot()["accepted_records"] == 2


def test_native_final_drain_delivers_batch_before_runner_and_rpc_cleanup(native_pair):
    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    master, worker, run = native_pair
    master.runner.start(1, spawn_rate=1)
    fire_request(worker)
    wrapper.cleanup_env(master)
    assert len(run.snapshot()) == 1
    assert master.record_delivery.snapshot()["error"] is None
    assert worker.record_delivery.snapshot()["pending_records"] == 0
    assert master.runner.server.socket.closed
    assert len(master.load_density_tasks) == 0


def test_native_lost_ack_retries_without_duplicate_results(native_pair, monkeypatch):
    module = delivery_module()
    master, worker, run = native_pair
    send = master.runner.send_message
    dropped = []
    def drop_first_ack(kind, data=None, client_id=None):
        if kind == module.ACK and not dropped:
            dropped.append(data)
            return
        send(kind, data, client_id=client_id)
    monkeypatch.setattr(master.runner, "send_message", drop_first_ack)
    fire_request(worker)
    until(lambda: worker.record_delivery.delivered == 1)
    assert len(run.snapshot()) == 1
    assert master.record_delivery.duplicates >= 1


def test_native_connection_reconnect_preserves_identity_and_pending_retry(native_pair):
    import gevent
    master, worker, run = native_pair
    producer = worker.record_delivery
    generation = producer.generation
    address = f"tcp://127.0.0.1:{master.runner.server.port}"
    worker.runner.client.socket.disconnect(address)
    fire_request(worker)
    gevent.sleep(0.02)
    worker.runner.client.socket.connect(address)
    until(lambda: producer.delivered == 1)
    assert producer.generation == generation
    assert run.snapshot()[0]["worker_id"] == worker.runner.client_id
    assert master.record_delivery.error is None


def test_native_cooperative_cancel_drains_and_cleans_owned_tasks(native_pair, monkeypatch):
    master, worker, run = native_pair
    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    def cancel():
        if worker.runner.user_count:
            fire_request(worker)
            return True
        return False
    env = wrapper.prepare_env(worker.user_classes[0], runner_mode="master", user_count=1,
                               test_time=None, stop_requested=cancel)
    assert env.cancellation_requested
    assert len(run.snapshot()) == 1
    assert len(env.load_density_tasks) == 0
    assert len(env.runner.greenlet) == 0
    assert env.record_delivery.error is None


def test_transport_failure_retains_pending_and_final_drain_reports_loss(monkeypatch):
    from locust.exception import RPCError
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(interval=0.001, drain_timeout=0.01))
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    def disconnect(*_args, **_kwargs):
        raise RPCError("disconnected")
    monkeypatch.setattr(env.runner, "send_message", disconnect)
    producer.flush()
    assert producer.snapshot()["pending_records"] == 1
    producer.close()
    assert producer.snapshot()["send_failures"] > 0
    assert "unacknowledged" in producer.snapshot()["error"]
    assert env.process_exit_code == 1


def test_late_ack_after_failed_close_preserves_loss_diagnostics():
    from types import SimpleNamespace
    module = delivery_module()
    env, sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(interval=0.001, drain_timeout=0.01))
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    producer.flush()
    original = sent[-1][1]
    producer.close()
    producer.on_ack(msg=SimpleNamespace(data={**original, "ok": True}))
    assert producer.snapshot()["pending_records"] == 1


def test_pending_byte_limit_is_independent_of_record_count():
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(max_record_bytes=1024, max_pending_bytes=1024))
    configure(producer)
    entry = {**legacy_entry(), "name": "x" * 300}
    producer.capture_legacy(entry, "passed")
    with pytest.raises(module.RecordDeliveryError, match="pending"):
        producer.capture_legacy(entry, "passed")
    assert producer.snapshot()["pending_bytes"] <= 1024
    assert producer.snapshot()["pending_records"] == 1
    env.load_density_tasks.kill()


def test_batch_byte_boundary_retains_remaining_records_until_next_ack():
    from types import SimpleNamespace
    module = delivery_module()
    env, sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(max_record_bytes=1024, max_batch_bytes=1400))
    configure(producer)
    for _ in range(3):
        producer.capture_legacy(legacy_entry(), "passed")
    producer.flush()
    first = sent[-1][1]
    assert len(module._encoded(first)) <= 1400
    assert len(first["records"]) < 3
    producer.on_ack(msg=SimpleNamespace(data={**first, "ok": True}))
    producer.flush()
    assert producer.frame["seq"] == 2
    assert producer.snapshot()["pending_records"] > 0


def test_master_conflicting_batch_retry_preserves_previously_accepted_results():
    from types import SimpleNamespace
    bridge, run, env, sent, _ = receiver()
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()])))
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured(name="changed")])))
    assert run.snapshot()[0]["name"] == "home"
    assert sent[-1][1]["ok"] is False
    env.load_density_tasks.kill()


def test_master_missing_worker_is_explicit_in_final_delivery_diagnostics():
    bridge, _run, env, _sent, _ = receiver()
    env.runner.clients["worker-a"].state = "missing"
    bridge.close()
    assert bridge.snapshot()["incomplete_workers"] == ["worker-a"]
    assert env.process_exit_code == 1


def test_new_epoch_rejects_late_batch_from_previous_generation():
    from types import SimpleNamespace
    bridge, run, env, sent, _ = receiver()
    bridge.on_hello(msg=SimpleNamespace(node_id="worker-a", data={"protocol": 1, "epoch": "producer-b",
                       "worker_id": "worker-a", "generation": 0, "run_id": None}))
    assert sent[-1][1]["generation"] == 2
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()])))
    assert run.snapshot() == []
    assert sent[-1][1]["ok"] is False
    env.load_density_tasks.kill()


def test_native_two_workers_final_flush_preserves_source_and_global_summary(native_pair):
    from je_load_density.utils.test_record.test_record_class import test_record_instance
    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    master, first, run = native_pair
    second = wrapper.create_env(first.user_classes[0], runner_mode="worker", master_host="127.0.0.1",
                                master_port=master.runner.server.port, distributed_records=True,
                                record_flush_interval=0.01, record_drain_timeout=2)
    try:
        until(lambda: master.record_delivery.ready_count == 2)
        fire_request(first)
        fire_request(second)
        wrapper.cleanup_env(master)
        assert len(run.snapshot()) == 2
        assert {record["worker_id"] for record in run.snapshot()} == {first.runner.client_id, second.runner.client_id}
        assert len(test_record_instance.test_record_list) == 2
        assert master.record_delivery.snapshot()["incomplete_workers"] == []
    finally:
        wrapper.cleanup_env(second)


def test_native_worker_local_stop_flushes_before_its_transport_closes(native_pair):
    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    master, worker, run = native_pair
    master.runner.start(1, spawn_rate=1)
    fire_request(worker)
    wrapper.cleanup_env(worker)
    until(lambda: len(run.snapshot()) == 1)
    assert worker.record_delivery.delivered == 1
    assert worker.runner.client.socket.closed
    assert len(worker.load_density_tasks) == 0


@pytest.mark.parametrize("options", [{"batch_size": 0}, {"max_pending": True}, {"interval": float("nan")},
                                     {"max_record_bytes": 262144}, {"max_pending_bytes": 1}])
def test_delivery_limits_reject_invalid_or_inconsistent_bounds(options):
    module = delivery_module()
    with pytest.raises(ValueError):
        module.DeliveryLimits(**options)


def test_workers_cannot_override_master_run_identity_before_connecting():
    from locust import User

    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    context = RunContext("loaddensity", "load", "locust")
    with pytest.raises(ValueError, match="receiving identity"):
        wrapper.create_env(User, runner_mode="worker", distributed_records=True, run_context=context)


def test_master_negotiated_bounds_limit_prehandshake_queue():
    from types import SimpleNamespace
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    producer.capture_legacy(legacy_entry(), "passed")
    producer.capture_legacy(legacy_entry(), "passed")
    producer.on_config(msg=SimpleNamespace(data={"protocol": 1, "run_id": "run-one", "source": "loaddensity",
        "phase": "load", "engine": "locust", "worker_id": "worker-a", "generation": 1,
        "epoch": producer.epoch, "limits": {**module.asdict(module.DeliveryLimits()), "max_pending": 1}}))
    assert producer.error is not None
    assert producer.identity is None
    assert producer.snapshot()["pending_records"] == 2
    env.load_density_tasks.kill()


def test_record_retry_in_new_sequence_does_not_duplicate_global_summary():
    from types import SimpleNamespace

    from je_load_density.utils.test_record.test_record_class import test_record_instance
    test_record_instance.clear_records()
    bridge, run, _env, sent, _ = receiver()
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()])))
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()], seq=2)))
    assert len(run.snapshot()) == 1
    assert len(test_record_instance.test_record_list) == 1
    assert sent[-1][1]["accepted"] == 0
    assert sent[-1][1]["ok"] is True
    test_record_instance.clear_records()


def test_master_malformed_record_rejects_valid_prefix_without_mutating():
    from types import SimpleNamespace
    bridge, run, env, sent, _ = receiver()
    records = [measured(), measured(identifier="record-two", schema_version=1)]
    records[1]["schema_version"] = 2
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame(records)))
    assert run.snapshot() == []
    assert sent[-1][1]["ok"] is False
    env.load_density_tasks.kill()


def test_master_batch_count_limit_rejects_before_atomic_ingest():
    from types import SimpleNamespace
    module = delivery_module()
    bridge, run, env, sent, _ = receiver()
    bridge.limits = module.DeliveryLimits(batch_size=1)
    records = [measured(), measured(identifier="record-two")]
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame(records)))
    assert run.snapshot() == []
    assert sent[-1][1]["ok"] is False
    env.load_density_tasks.kill()


def test_aggregate_sqlite_roundtrip_preserves_worker_provenance_and_deduplication(tmp_path):
    from je_load_density.utils.test_record.sqlite_persistence import fetch_canonical_records, persist_canonical_records
    run = aggregate()
    run.ingest_batch("worker-a", [measured()])
    run.ingest_batch("worker-b", [measured("worker-b", "record-two")])
    database = str(tmp_path / "distributed.sqlite")
    assert persist_canonical_records(database, run) == run.run_id
    persist_canonical_records(database, run)
    assert fetch_canonical_records(database, run.run_id) == run.snapshot()


def test_stalled_native_send_does_not_exceed_final_drain_budget(monkeypatch):
    import gevent
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits(interval=0.001, drain_timeout=0.01))
    configure(producer)
    producer.capture_legacy(legacy_entry(), "passed")
    def stalled_send(*_args, **_kwargs):
        gevent.sleep(1)
    monkeypatch.setattr(env.runner, "send_message", stalled_send)
    with gevent.Timeout(0.1):
        producer.close()
    assert producer.snapshot()["pending_records"] == 1
    assert producer.snapshot()["error"] is not None
    assert producer.snapshot()["send_failures"] > 0


def test_stale_config_cannot_mutate_bounds_or_fail_pending_queue():
    from types import SimpleNamespace
    module = delivery_module()
    env, _, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    configure(producer, generation=2)
    producer.capture_legacy(legacy_entry(), "passed")
    producer.capture_legacy(legacy_entry(), "passed")
    original = producer.limits
    producer.on_config(msg=SimpleNamespace(data={"protocol": 1, "run_id": "run-one", "source": "loaddensity",
        "phase": "load", "engine": "locust", "worker_id": "worker-a", "generation": 1,
        "epoch": producer.epoch, "limits": {**module.asdict(module.DeliveryLimits()), "max_pending": 1}}))
    assert producer.limits == original
    assert producer.error is None
    assert producer.generation == 2
    assert producer.snapshot()["pending_records"] == 2
    env.load_density_tasks.kill()


def test_cleanup_delivery_error_preserves_original_environment_callback_failure(monkeypatch):
    from locust import User, runners

    from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper
    env = wrapper.create_env(User, runner_mode="master", master_bind_port=0, run_context=aggregate())
    env.runner.clients["unbound-worker"] = runners.WorkerNode("unbound-worker")
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: env)
    def rejected(_env):
        raise RuntimeError("environment callback failed")
    with pytest.raises(RuntimeError, match="environment callback failed"):
        wrapper.prepare_env(User, runner_mode="master", on_environment=rejected)
    assert env.record_delivery.error is not None
    assert env.runner.server.socket.closed
    assert len(env.load_density_tasks) == 0


@pytest.mark.parametrize("extra", ["oversized_nonce", "unknown_field"])
def test_invalid_done_control_cannot_finish_session_or_reflect_oversized_payload(extra):
    from types import SimpleNamespace
    module = delivery_module()
    bridge, _run, _env, sent, _ = receiver()
    data = {"protocol": 1, "run_id": "run-one", "worker_id": "worker-a", "epoch": "producer-a",
            "generation": 1, "nonce": "terminal", "pending": 0}
    if extra == "oversized_nonce":
        data["nonce"] = "x" * (bridge.limits.max_batch_bytes + 1)
    else:
        data["extra"] = "x" * (bridge.limits.max_batch_bytes + 1)
    bridge._on_done(msg=SimpleNamespace(node_id="worker-a", data=data))
    assert bridge.sessions["worker-a"].finished is False
    assert bridge.rejected == 1
    assert all(kind != module.FINISHED for kind, _payload, _target in sent)


def test_valid_done_control_acknowledges_only_expected_bounded_fields():
    from types import SimpleNamespace
    module = delivery_module()
    bridge, _run, _env, sent, _ = receiver()
    data = {"protocol": 1, "run_id": "run-one", "worker_id": "worker-a", "epoch": "producer-a",
            "generation": 1, "nonce": "terminal", "pending": 0}
    bridge._on_done(msg=SimpleNamespace(node_id="worker-a", data=data))
    assert bridge.sessions["worker-a"].finished is True
    assert sent[-1][0] == module.FINISHED
    assert sent[-1][1] == data
    assert len(module._encoded(sent[-1][1])) <= bridge.limits.max_batch_bytes


def test_invalid_flush_control_does_not_spawn_drain_or_echo_nonce():
    from types import SimpleNamespace
    module = delivery_module()
    env, sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    configure(producer)
    producer._on_flush(msg=SimpleNamespace(data={"run_id": "run-one", "nonce": "x" * 129}))
    assert len(env.load_density_tasks) == 0
    assert all(kind != module.DONE for kind, _payload, _target in sent)


def test_invalid_finished_control_does_not_finalize_producer():
    from types import SimpleNamespace
    module = delivery_module()
    env, _sent, _ = fake_environment()
    producer = module.WorkerRecords(env, module.DeliveryLimits())
    configure(producer)
    producer._final_nonce = "terminal"
    producer._on_finished(msg=SimpleNamespace(data={**producer._base(), "nonce": "terminal", "pending": 0,
                                                   "extra": "x" * 129}))
    assert producer.finalized is False


def test_retired_bootstrap_hello_cannot_resurrect_epoch_or_poison_current_producer():
    from types import SimpleNamespace
    module = delivery_module()
    module.test_record_instance.clear_records()
    bridge, run, env, sent, _ = receiver()
    bridge.on_hello(msg=SimpleNamespace(node_id="worker-a", data={"protocol": 1, "epoch": "producer-b",
                       "worker_id": "worker-a", "generation": 0, "run_id": None}))
    configured = sent[-1][1]
    bridge.on_hello(msg=SimpleNamespace(node_id="worker-a", data={"protocol": 1, "epoch": "producer-a",
                       "worker_id": "worker-a", "generation": 0, "run_id": None}))
    assert bridge.sessions["worker-a"].epoch == "producer-b"
    assert bridge.sessions["worker-a"].generation == 2
    assert bridge.error is None
    bridge.on_batch(msg=SimpleNamespace(node_id="worker-a", data=frame([measured()], epoch="producer-b",
                           generation=configured["generation"])))
    assert len(run.snapshot()) == 1
    assert sent[-1][1]["ok"] is True
    module.test_record_instance.clear_records()
    env.load_density_tasks.kill()


def test_retired_epoch_capacity_fails_without_eviction_or_session_mutation(monkeypatch):
    from types import SimpleNamespace
    module = delivery_module()
    monkeypatch.setattr(module, "RETIRED_EPOCH_LIMIT", 1)
    bridge, _run, env, _sent, _ = receiver()
    for epoch in ("producer-b", "producer-c"):
        bridge.on_hello(msg=SimpleNamespace(node_id="worker-a", data={"protocol": 1, "epoch": epoch,
                           "worker_id": "worker-a", "generation": 0, "run_id": None}))
    assert bridge.error is not None
    assert "retired" in str(bridge.error)
    assert bridge.sessions["worker-a"].epoch == "producer-b"
    assert bridge.sessions["worker-a"].generation == 2
    assert bridge.sessions["worker-a"].retired_epochs == {"producer-a"}
    assert env.process_exit_code == 1
    env.load_density_tasks.kill()
