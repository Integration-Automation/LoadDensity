from typing import Any, Dict, List, Optional

import gevent
from locust import User, events
from locust.env import Environment
from locust.log import setup_logging
from locust.stats import stats_history, stats_printer

from je_load_density.utils.logging.loggin_instance import load_density_logger

setup_logging("INFO", None)


def prepare_env(
    user_class: List[User],
    user_count: int = 50,
    spawn_rate: int = 10,
    test_time: Optional[int] = 60,
    web_ui_dict: Optional[Dict[str, Any]] = None,
    runner_mode: str = "local",
    master_bind_host: str = "*",
    master_bind_port: int = 5557,
    master_host: str = "127.0.0.1",
    master_port: int = 5557,
    expected_workers: int = 0,
    **kwargs,
):
    """
    啟動 Locust 環境，支援 local / master / worker 三種模式。
    Prepare a Locust environment in local, master, or worker mode.
    """
    load_density_logger.info(
        f"prepare_env mode={runner_mode}, user_class={user_class}, user_count={user_count}, "
        f"spawn_rate={spawn_rate}, test_time={test_time}, web_ui_dict={web_ui_dict}"
    )

    env = create_env(user_class, runner_mode=runner_mode,
                     master_bind_host=master_bind_host, master_bind_port=master_bind_port,
                     master_host=master_host, master_port=master_port)

    if runner_mode == "worker":
        env.runner.greenlet.join()
        return env

    if runner_mode == "master" and expected_workers > 0:
        _wait_for_workers(env, expected_workers)

    env.runner.start(user_count, spawn_rate=spawn_rate)

    if web_ui_dict is not None:
        env.create_web_ui(web_ui_dict.get("host", "127.0.0.1"), web_ui_dict.get("port", 8089))

    if test_time is not None:
        gevent.spawn_later(test_time, env.runner.quit)

    env.runner.greenlet.join()

    if web_ui_dict is not None and getattr(env, "web_ui", None) is not None:
        env.web_ui.stop()

    return env


def create_env(
    user_class: List[User],
    another_event: events = events,
    runner_mode: str = "local",
    master_bind_host: str = "*",
    master_bind_port: int = 5557,
    master_host: str = "127.0.0.1",
    master_port: int = 5557,
):
    """
    建立 Locust Environment 並依模式建立 runner。
    Create Locust Environment and build the matching runner.
    """
    load_density_logger.info(
        f"create_env mode={runner_mode}, user_class={user_class}, another_event={another_event}"
    )
    env = Environment(user_classes=[user_class], events=another_event)

    if runner_mode == "master":
        env.create_master_runner(master_bind_host=master_bind_host, master_bind_port=master_bind_port)
    elif runner_mode == "worker":
        env.create_worker_runner(master_host=master_host, master_port=master_port)
    else:
        env.create_local_runner()

    if runner_mode != "worker":
        gevent.spawn(stats_printer(env.stats))
        gevent.spawn(stats_history, env.runner)
    return env


def _wait_for_workers(env, expected_workers: int, timeout: float = 60.0) -> None:
    """
    等待指定數量的 worker 加入後再開始壓測。
    """
    deadline = gevent.time.time() + timeout
    while gevent.time.time() < deadline:
        workers = getattr(env.runner, "clients", None)
        connected = len(workers) if workers is not None else 0
        if connected >= expected_workers:
            return
        gevent.sleep(0.5)
    load_density_logger.warning(
        f"only {connected}/{expected_workers} workers joined within {timeout}s; starting anyway"
    )
