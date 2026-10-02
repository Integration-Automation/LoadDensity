from functools import partial
from time import monotonic
from typing import Any, Dict, Optional

import gevent
from gevent.pool import Group
from locust import User, events
from locust.argument_parser import get_parser
from locust.env import Environment
from locust.event import Events
from locust.log import setup_logging
from locust.stats import stats_history, stats_printer

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.wrapper.distributed_config import DistributedConfig, NativeHeartbeatScope
from je_load_density.wrapper.distributed_health import DistributedHealth

setup_logging("INFO", None)


def prepare_env(
    user_class: type[User],
    user_count: int = 50,
    spawn_rate: int = 10,
    test_time: Optional[int] = 60,
    web_ui_dict: Optional[Dict[str, Any]] = None,
    runner_mode: str = "local",
    load_shape: Optional[str] = None,
    shape_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Environment:
    """
    啟動 Locust 環境。Prepare a Locust environment in local, master, or worker mode.

    Distributed-mode and worker-health settings are read from ``**kwargs``.

    Worker timing defaults are startup=60, heartbeat=5 and lost=15 seconds. Startup
    fails and cleans up unless ``worker_startup_policy="degraded"`` permits
    fewer healthy ready workers; at least one is always required. All nodes
    must use matching heartbeat settings. Native detection uses interval ticks.
    ``on_environment(env)`` runs before the ready gate in the execution thread.
    ``stop_requested()`` cooperatively cancels startup or running work.
    This function owns and closes the environment's resources before returning.
    Callback errors propagate to the caller after cleanup, including during ramp-up.
    """
    master_bind_host = kwargs.pop("master_bind_host", "*")
    master_bind_port = kwargs.pop("master_bind_port", 5557)
    master_host = kwargs.pop("master_host", "127.0.0.1")
    master_port = kwargs.pop("master_port", 5557)
    config = DistributedConfig.from_options(kwargs)
    stop_requested = kwargs.pop("stop_requested", None)
    on_environment = kwargs.pop("on_environment", None)
    run_context = kwargs.pop("run_context", None)
    if run_context is None:
        from je_load_density.utils.test_record.contract import get_optional_run_context
        run_context = get_optional_run_context()

    load_density_logger.info(
        f"prepare_env mode={runner_mode}, user_class={user_class}, user_count={user_count}, "
        f"spawn_rate={spawn_rate}, test_time={test_time}, web_ui_dict={web_ui_dict}, "
        f"load_shape={load_shape}"
    )

    env = create_env(user_class, runner_mode=runner_mode,
                     master_bind_host=master_bind_host, master_bind_port=master_bind_port,
                     master_host=master_host, master_port=master_port,
                     load_shape=load_shape, shape_config=shape_config, run_context=run_context,
                     **kwargs)
    try:
        if not _prepare_start(env, runner_mode, config, stop_requested, on_environment):
            return env
        if runner_mode != "worker":
            if not _start_controller_load(env, user_count, spawn_rate, web_ui_dict, test_time):
                return env
        env.runner.greenlet.join()
        _raise_cancellation_error(env)
    finally:
        cleanup_env(env)
    return env


def _prepare_start(env: Environment, runner_mode: str, config: DistributedConfig,
                   stop_requested, on_environment) -> bool:
    """Notify the caller, satisfy master readiness, then start cancellation observation."""
    if on_environment is not None:
        on_environment(env)
    if stop_requested is not None and stop_requested():
        return False
    if runner_mode == "master":
        _wait_for_workers(env, max(1, config.expected_workers), timeout=config.startup_timeout,
                          policy=config.startup_policy, stop_requested=stop_requested)
        if stop_requested is not None and stop_requested():
            return False
    if stop_requested is not None:
        env.load_density_tasks.spawn(_watch_cancel, env, stop_requested)
    return True


def _start_controller_load(env: Environment, user_count: int, spawn_rate: int,
                           web_ui_dict: Optional[Dict[str, Any]], test_time: Optional[int]) -> bool:
    """Start a controller's native shape or owned ramp before optional UI and timer setup."""
    if env.shape_class is not None:
        env.runner.start_shape()
    else:
        env.startup_task = env.load_density_tasks.spawn(env.runner.start, user_count, spawn_rate=spawn_rate)
        env.startup_task.get()
    _raise_cancellation_error(env)
    if env.cancellation_requested:
        return False
    if web_ui_dict is not None:
        env.create_web_ui(web_ui_dict.get("host", "127.0.0.1"), web_ui_dict.get("port", 8089))
    if test_time is not None:
        env.load_density_tasks.add(gevent.spawn_later(test_time, env.runner.quit))
    return True


def _raise_cancellation_error(env: Environment) -> None:
    if env.cancellation_error is not None:
        raise env.cancellation_error


def create_env(
    user_class: type[User],
    another_event: Events = events,
    runner_mode: str = "local",
    master_bind_host: str = "*",
    master_bind_port: int = 5557,
    master_host: str = "127.0.0.1",
    master_port: int = 5557,
    load_shape: Optional[str] = None,
    shape_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Environment:
    """
    建立 Locust Environment 並依模式建立 runner。
    Create Locust Environment and build the matching runner.

    Call ``cleanup_env`` when the caller has finished with the environment.
    Master health is available as ``env.distributed_health.snapshot()``;
    request health and worker health are separate. Distributed environments
    in the same process must share heartbeat timing settings.
    """
    load_density_logger.info(
        f"create_env mode={runner_mode}, user_class={user_class}, another_event={another_event}"
    )
    if runner_mode not in ("local", "master", "worker"):
        raise ValueError("runner_mode must be local, master or worker")
    config = DistributedConfig.from_options(kwargs)
    shape_class = _resolve_shape(load_shape, shape_config)
    run_context = kwargs.pop("run_context", None)
    if run_context is not None:
        from je_load_density.wrapper.event.request_hook import request_hook
        if another_event is not events:
            raise ValueError("a canonical run context requires an isolated default event environment")
        another_event = Events()
        another_event.request.add_listener(partial(request_hook, record_run=run_context))
    if another_event is events and runner_mode != "local":
        # Shared global event hooks would let one master's quit stop another run.
        another_event = Events()
        from je_load_density.wrapper.event.request_hook import request_hook
        another_event.request.add_listener(request_hook)
    options = None
    scope = None
    if runner_mode != "local" or shape_class is not None:
        options = get_parser(default_config_files=[]).parse_args(args=[])
        options.enable_rebalancing = True
        options.headless = True
    env = Environment(user_classes=[user_class], events=another_event,
                      shape_class=shape_class, parsed_options=options)
    if runner_mode != "local":
        scope = NativeHeartbeatScope(config)
    env.load_density_tasks = Group()
    env.native_heartbeat_scope = scope
    env.load_density_closed = False
    env.cancellation_error = None
    env.cancellation_requested = False
    env.startup_task = None
    runner_created = False
    try:
        _create_runner(env, runner_mode, master_bind_host, master_bind_port, master_host, master_port)
        if runner_mode == "master":
            env.distributed_health = DistributedHealth(env, config)
            env.load_density_tasks.spawn(env.distributed_health.monitor)
        if runner_mode != "worker":
            env.load_density_tasks.spawn(stats_printer(env.stats))
            env.load_density_tasks.spawn(stats_history, env.runner)
        runner_created = True
    finally:
        if not runner_created:
            cleanup_env(env)
    return env


def _resolve_shape(load_shape: Optional[str], shape_config: Optional[Dict[str, Any]]):
    if not load_shape:
        return None
    from je_load_density.utils.load_shapes.shapes import build_load_shape
    return build_load_shape(load_shape, shape_config or {})()


def _create_runner(env, mode, bind_host, bind_port, host, port) -> None:
    if mode == "master":
        env.create_master_runner(master_bind_host=bind_host, master_bind_port=bind_port)
    elif mode == "worker":
        env.create_worker_runner(master_host=host, master_port=port)
    else:
        env.create_local_runner()


def _wait_for_workers(env, expected_workers: int, timeout: float = 60.0,
                      policy: str = "fail", stop_requested=None) -> None:
    """Wait for healthy ready workers; fail closed unless degraded startup is explicit."""
    deadline = monotonic() + timeout
    while True:
        connected = env.distributed_health.ready_count
        if connected >= expected_workers:
            return
        if stop_requested is not None and stop_requested():
            return
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        gevent.sleep(min(0.1, remaining))
    message = f"only {connected}/{expected_workers} healthy ready workers joined within {timeout}s"
    if policy == "degraded" and connected:
        env.distributed_health.degraded_startup(expected_workers, message)
        load_density_logger.warning(message)
        return
    env.distributed_health.fail(message)
    raise TimeoutError(message)


def _watch_cancel(env, stop_requested) -> None:
    while env.runner.greenlet:
        try:
            should_stop = stop_requested()
        except Exception as error:
            # User callbacks can raise any Exception; propagate it in the caller's
            # execution thread after the native runner is stopped and cleaned up.
            env.cancellation_error = error
            health = getattr(env, "distributed_health", None)
            if health is not None:
                health.fail("stop_requested callback failed")
            _stop_owned_run(env)
            return
        if should_stop:
            _stop_owned_run(env)
            return
        gevent.sleep(0.05)


def _stop_owned_run(env: Environment) -> None:
    env.cancellation_requested = True
    if env.startup_task is not None and not env.startup_task.dead:
        env.startup_task.kill(block=True)
    env.runner.quit()


def cleanup_env(env: Environment) -> None:
    """Close owned runner, UI, auxiliary greenlets, RPC transport, and timing scope once."""
    if getattr(env, "load_density_closed", False):
        return
    env.load_density_closed = True
    health = getattr(env, "distributed_health", None)
    if health is not None:
        health.close()
    try:
        if env.runner is not None and env.runner.greenlet:
            env.runner.quit()
    finally:
        try:
            env.load_density_tasks.kill(block=True)
            if env.web_ui is not None:
                env.web_ui.stop()
        finally:
            _close_distributed_resources(env)


def _close_distributed_resources(env: Environment) -> None:
    try:
        if env.runner is not None:
            transport = getattr(env.runner, "server", None) or getattr(env.runner, "client", None)
            if transport is not None:
                transport.close(linger=0)
    finally:
        if env.native_heartbeat_scope is not None:
            env.native_heartbeat_scope.close()
