"""Distributed lifecycle contract, with native runners and controlled RPC messages."""
from types import SimpleNamespace

import gevent
import pytest
from locust import User, runners, task
from locust.event import Events
from locust.rpc import Message

from je_load_density.wrapper.create_locust_env import create_locust_env as wrapper


class IdleUser(User):
    @task
    def idle(self):
        gevent.sleep(0.01)


@pytest.fixture
def master():
    env = wrapper.create_env(IdleUser, another_event=Events(), runner_mode="master", master_bind_port=0,
                             worker_heartbeat_interval=0.02, worker_lost_timeout=0.06)
    yield env
    wrapper.cleanup_env(env)


@pytest.mark.parametrize("options", [
    {"worker_startup_timeout": 0}, {"worker_heartbeat_interval": -1},
    {"worker_lost_timeout": float("nan")}, {"worker_lost_timeout": 5},
    {"worker_startup_policy": "anyway"}, {"expected_workers": -1},
])
def test_invalid_distributed_settings_rejected_before_runner_creation(options):
    env = None
    try:
        with pytest.raises(ValueError):
            env = wrapper.create_env(IdleUser, runner_mode="master", master_bind_port=0, **options)
    finally:
        if env is not None:
            wrapper.cleanup_env(env)


def test_ready_gate_excludes_missing_running_and_expired_workers(master):
    master.runner.clients["ready"] = runners.WorkerNode("ready", heartbeat_liveness=1)
    master.runner.clients["lost"] = runners.WorkerNode("lost", state="missing")
    master.runner.clients["running"] = runners.WorkerNode("running", state="running")
    master.runner.clients["expired"] = runners.WorkerNode("expired", heartbeat_liveness=-1)
    assert master.distributed_health.ready_count == 1
    with pytest.raises(TimeoutError):
        wrapper._wait_for_workers(master, 2, timeout=0.01)


def test_native_settings_restore_after_last_environment_cleanup():
    original = (runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS)
    env = wrapper.create_env(IdleUser, another_event=Events(), runner_mode="master", master_bind_port=0)
    try:
        assert runners.HEARTBEAT_INTERVAL == 5
        assert env.runner.rebalancing_enabled()
        with pytest.raises(ValueError, match="conflicting"):
            wrapper.create_env(IdleUser, runner_mode="master", master_bind_port=0, worker_heartbeat_interval=2)
    finally:
        wrapper.cleanup_env(env)
    current_timing = runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS
    assert current_timing == original


def test_prepare_env_startup_timeout_never_starts_and_cleans_runner(monkeypatch, master):
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    with pytest.raises(TimeoutError):
        wrapper.prepare_env(IdleUser, runner_mode="master", expected_workers=1, worker_startup_timeout=0.01)
    assert master.runner.target_user_count == 0
    assert len(master.runner.greenlet) == 0
    assert master.distributed_health.snapshot()["status"] == "failed"
    assert master.runner.server.socket.closed


def test_explicit_degraded_startup_requires_at_least_one_worker(monkeypatch, master):
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    with pytest.raises(TimeoutError):
        wrapper.prepare_env(IdleUser, runner_mode="master", expected_workers=2, worker_startup_timeout=0.01,
                            worker_startup_policy="degraded")
    assert master.runner.target_user_count == 0


def test_cancel_callback_follows_environment_setup_and_cleans_greenlets():
    seen = []
    def created(env):
        assert env.runner is not None
        seen.append(env)
    with gevent.Timeout(1):
        env = wrapper.prepare_env(IdleUser, user_count=1, test_time=None, on_environment=created,
                                  stop_requested=lambda: bool(seen))
    assert seen == [env]
    assert len(env.runner.greenlet) == 0
    assert len(env.runner.user_greenlets) == 0
    assert len(env.load_density_tasks) == 0


def _controlled_workers(env, monkeypatch, worker_ids=("first", "second")):
    """Keep native runner/dispatcher real; replace only RPC wire delivery."""
    sent = []
    active = set(worker_ids)
    def deliver(message):
        if message.type == "spawn":
            sent.append((gevent.time.monotonic(), message.node_id, message.data["user_classes_count"]))
            env.runner.handle_message(message.node_id, Message("spawning_complete", {
                "user_classes_count": message.data["user_classes_count"]}, message.node_id))
        elif message.type == "stop":
            env.runner.clients[message.node_id].user_classes_count = {}
    monkeypatch.setattr(env.runner.server, "send_to_client", deliver)
    for worker_id in worker_ids:
        env.runner.handle_message(worker_id, Message("client_ready", -1, worker_id))
    def beat():
        while True:
            for worker_id in list(active):
                if worker_id in env.runner.clients:
                    state = env.runner.clients[worker_id].state
                    env.runner.handle_message(worker_id, Message("heartbeat", {
                        "state": state, "current_cpu_usage": 0}, worker_id))
            gevent.sleep(0.005)
    env.load_density_tasks.spawn(beat)
    return sent, active


def _until(predicate, timeout=2):
    with gevent.Timeout(timeout):
        while not predicate():
            gevent.sleep(0.005)


def test_health_waits_for_native_missing_before_marking_worker_lost(master):
    master.runner.clients["pending"] = runners.WorkerNode("pending", state="running", heartbeat_liveness=-1)
    master.distributed_health.refresh()
    assert master.distributed_health.snapshot()["workers"]["pending"] == "running"


def test_native_network_loss_rebalances_capacity_at_original_target_and_rate(master, monkeypatch):
    sent, active = _controlled_workers(master, monkeypatch)
    master.runner.start(4, spawn_rate=4)
    active.remove("second")
    _until(lambda: master.runner.clients["second"].state == "missing")
    _until(lambda: master.runner.clients["first"].user_count == 4)
    snapshot = master.distributed_health.snapshot()
    assert snapshot["target_users"] == 4
    assert snapshot["reported_users"] == 4
    assert snapshot["affected_workers"] == ["second"]
    assert snapshot["request_replay"] is False
    assert master.runner.spawn_rate == 4
    assert sent[-1][1:] == ("first", {"IdleUser": 4})


def test_native_late_heartbeat_rejoins_without_double_assignment(master, monkeypatch):
    _, active = _controlled_workers(master, monkeypatch)
    master.runner.start(4, spawn_rate=100)
    active.remove("second")
    _until(lambda: master.runner.clients["second"].state == "missing")
    master.runner.handle_message("second", Message("heartbeat", {
        "state": "running", "current_cpu_usage": 0}, "second"))
    active.add("second")
    _until(lambda: master.runner.user_count == 4)
    assert sum(client.user_count for client in master.runner.clients.all) == 4
    assert len(master.runner.clients) == 2
    assert master.distributed_health.snapshot()["workers"]["second"] == "running"


def test_native_duplicate_ready_keeps_one_worker_assignment(master, monkeypatch):
    _controlled_workers(master, monkeypatch)
    master.runner.start(4, spawn_rate=100)
    master.runner.handle_message("second", Message("client_ready", -1, "second"))
    assert len(master.runner.clients) == 2
    assert master.runner.user_count == 4


def test_native_worker_quit_redistributes_users(master, monkeypatch):
    _, active = _controlled_workers(master, monkeypatch)
    master.runner.start(4, spawn_rate=100)
    active.remove("second")
    master.runner.handle_message("second", Message("quit", None, "second"))
    assert master.runner.user_count == 4
    assert master.distributed_health.snapshot()["affected_workers"] == ["second"]


def test_all_workers_lost_marks_failed_and_terminates_master(master, monkeypatch):
    _, active = _controlled_workers(master, monkeypatch)
    master.runner.start(2, spawn_rate=100)
    active.clear()
    _until(lambda: not master.runner.greenlet)
    assert master.distributed_health.snapshot()["status"] == "failed"
    assert master.process_exit_code == 1
    assert set(master.distributed_health.snapshot()["affected_workers"]) == {"first", "second"}


def test_native_loss_during_ramp_retains_total_and_spawn_constraint(master, monkeypatch):
    sent, active = _controlled_workers(master, monkeypatch)
    ramp = gevent.spawn(master.runner.start, 6, spawn_rate=2)
    _until(lambda: master.runner.user_count >= 2)
    active.remove("second")
    ramp.get(timeout=5)
    _until(lambda: master.runner.spawning_completed and master.runner.user_count == 6, timeout=5)
    assert master.runner.user_count == 6
    assert master.runner.target_user_count == 6
    assert master.runner.spawn_rate == 2
    assert sent[-1][0] - sent[0][0] >= 1.8


def test_observed_capacity_shortfall_is_degraded(master, monkeypatch):
    _controlled_workers(master, monkeypatch)
    master.runner.start(4, spawn_rate=100)
    master.runner.clients["second"].user_classes_count = {"IdleUser": 0}
    assert master.distributed_health.snapshot()["status"] == "degraded"
    master.runner.clients["second"].user_classes_count = {"IdleUser": 2}
    master.runner.worker_cpu_warning_emitted = True
    assert master.distributed_health.snapshot()["status"] == "degraded"


def test_cancel_during_startup_does_not_start_users(monkeypatch, master):
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    stop = iter((False, True, True))
    wrapper.prepare_env(IdleUser, runner_mode="master", expected_workers=1,
                        stop_requested=lambda: next(stop, True))
    assert master.runner.target_user_count == 0


def test_callback_error_cleans_transport_and_settings(monkeypatch, master):
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    def rejected(_env):
        raise RuntimeError("callback failed")
    with pytest.raises(RuntimeError, match="callback failed"):
        wrapper.prepare_env(IdleUser, on_environment=rejected)
    assert master.runner.server.socket.closed
    assert len(master.load_density_tasks) == 0


def test_shape_changes_native_target_and_finishes_without_hanging(monkeypatch):
    seen = []
    def created(env):
        _controlled_workers(env, monkeypatch)
        shape_time = iter((0.0, 1.0, 2.0))
        monkeypatch.setattr(env.shape_class, "get_run_time", lambda: next(shape_time))
        env.events.spawning_complete.add_listener(lambda **_kw: seen.append(env.runner.target_user_count))
    with gevent.Timeout(5):
        env = wrapper.prepare_env(IdleUser, runner_mode="master", master_bind_port=0,
                                  expected_workers=2, test_time=None,
                                  worker_heartbeat_interval=0.02, worker_lost_timeout=0.06,
                                  load_shape="stages", shape_config={"stages": [
                                      {"duration": 1, "users": 2, "spawn_rate": 100},
                                      {"duration": 1, "users": 4, "spawn_rate": 100}]},
                                  on_environment=created)
    assert seen[:2] == [2, 4]
    assert len(env.runner.greenlet) == 0
    assert env.runner.server.socket.closed


def test_degraded_startup_reports_shortfall_after_cleanup(monkeypatch, master):
    monkeypatch.setattr(wrapper, "create_env", lambda *_args, **_kwargs: master)
    _controlled_workers(master, monkeypatch, worker_ids=("first",))
    env = wrapper.prepare_env(IdleUser, runner_mode="master", expected_workers=2, user_count=2,
                              spawn_rate=100, worker_startup_timeout=0.01,
                              worker_startup_policy="degraded", test_time=0.01)
    assert env.distributed_health.snapshot()["status"] == "degraded"


def test_cancel_stops_running_local_users_and_timer():
    seen = []
    with gevent.Timeout(3):
        env = wrapper.prepare_env(IdleUser, user_count=2, test_time=60, on_environment=seen.append,
                                  stop_requested=lambda: bool(seen and seen[0].runner.user_count))
    assert len(env.runner.user_greenlets) == 0
    assert len(env.load_density_tasks) == 0


def test_matching_environment_scope_restores_only_after_last_close():
    original = (runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS)
    first = wrapper.create_env(IdleUser, runner_mode="master", master_bind_port=0)
    second = wrapper.create_env(IdleUser, runner_mode="master", master_bind_port=0)
    try:
        wrapper.cleanup_env(first)
        assert runners.HEARTBEAT_INTERVAL == 5
        wrapper.cleanup_env(first)
        assert runners.HEARTBEAT_INTERVAL == 5
    finally:
        wrapper.cleanup_env(second)
    current_timing = runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS
    assert current_timing == original


def test_real_rpc_worker_connects_runs_and_closes_both_transports(master):
    worker = wrapper.create_env(IdleUser, another_event=Events(), runner_mode="worker",
                                master_host="127.0.0.1", master_port=master.runner.server.port,
                                worker_heartbeat_interval=0.02, worker_lost_timeout=0.06)
    try:
        _until(lambda: master.distributed_health.ready_count == 1)
        master.runner.start(2, spawn_rate=100)
        _until(lambda: worker.runner.user_count == 2)
        assert master.distributed_health.snapshot()["reported_users"] == 2
    finally:
        wrapper.cleanup_env(worker)
    assert worker.runner.client.socket.closed
    assert len(worker.runner.user_greenlets) == 0
    assert len(worker.runner.greenlet) == 0


def test_cleanup_ui_error_still_closes_transport_and_restores_settings():
    original = (runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS)
    env = wrapper.create_env(IdleUser, runner_mode="master", master_bind_port=0)
    def broken_stop():
        raise RuntimeError("UI stop failed")
    env.web_ui = SimpleNamespace(stop=broken_stop)
    with pytest.raises(RuntimeError, match="UI stop failed"):
        wrapper.cleanup_env(env)
    assert env.runner.server.socket.closed
    current_timing = runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS
    assert current_timing == original


def test_local_shape_completes_and_releases_tasks(monkeypatch):
    def created(env):
        shape_time = iter((0.0, 1.0))
        monkeypatch.setattr(env.shape_class, "get_run_time", lambda: next(shape_time))
    with gevent.Timeout(3):
        env = wrapper.prepare_env(IdleUser, test_time=None, load_shape="stages",
                                  shape_config={"stages": [{"duration": 1, "users": 1, "spawn_rate": 100}]},
                                  on_environment=created)
    assert len(env.runner.greenlet) == 0
    assert len(env.load_density_tasks) == 0


def test_running_stop_callback_error_propagates_and_cleans_resources():
    seen = []
    calls = 0
    def broken_stop():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise RuntimeError("stop callback failed")
        return False
    with gevent.Timeout(1):
        with pytest.raises(RuntimeError, match="stop callback failed"):
            wrapper.prepare_env(IdleUser, user_count=2, test_time=None,
                                on_environment=seen.append, stop_requested=broken_stop)
    assert len(seen[0].runner.greenlet) == 0
    assert len(seen[0].runner.user_greenlets) == 0
    assert len(seen[0].load_density_tasks) == 0


def test_master_stop_callback_error_propagates_and_restores_settings(monkeypatch):
    original = (runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS)
    seen = []
    calls = 0
    def created(env):
        seen.append(env)
        _controlled_workers(env, monkeypatch)
    def broken_stop():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise RuntimeError("master stop callback failed")
        return False
    with gevent.Timeout(2):
        with pytest.raises(RuntimeError, match="master stop callback failed"):
            wrapper.prepare_env(IdleUser, runner_mode="master", master_bind_port=0, expected_workers=2,
                                user_count=2, spawn_rate=100, test_time=None,
                                on_environment=created, stop_requested=broken_stop)
    assert seen[0].runner.server.socket.closed
    assert len(seen[0].load_density_tasks) == 0
    current_timing = runners.HEARTBEAT_INTERVAL, runners.HEARTBEAT_LIVENESS
    assert current_timing == original


def test_master_stop_callback_error_interrupts_slow_ramp(monkeypatch):
    seen = []
    def created(env):
        seen.append(env)
        _controlled_workers(env, monkeypatch)
    def broken_stop():
        if seen and seen[0].runner.user_count >= 1:
            raise RuntimeError("ramp callback failed")
        return False
    with gevent.Timeout(2):
        with pytest.raises(RuntimeError, match="ramp callback failed"):
            wrapper.prepare_env(IdleUser, runner_mode="master", master_bind_port=0, expected_workers=2,
                                user_count=10, spawn_rate=1, test_time=None,
                                on_environment=created, stop_requested=broken_stop)
    assert len(seen[0].runner.greenlet) == 0
    assert len(seen[0].load_density_tasks) == 0
    assert seen[0].runner.server.socket.closed
