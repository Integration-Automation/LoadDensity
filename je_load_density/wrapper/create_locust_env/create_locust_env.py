import gevent
from locust import User
from locust import events
from locust.env import Environment
from locust.log import setup_logging
from locust.stats import stats_printer, stats_history

from je_load_density.utils.logging.loggin_instance import load_density_logger

setup_logging("INFO", None)


def prepare_env(user_class: [User], user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
                web_ui_dict: dict = None,
                **kwargs):
    """
    :param user_class: locust user class
    :param user_count: how many user we want to spawn
    :param spawn_rate: one time will spawn how many user
    :param test_time: total test run time
    :param web_ui_dict: web ui dict include host and port like {"host": "127.0.0.1", "port": 8089}
    :param kwargs: to catch unknown param
    :return: None
    """
    load_density_logger.info(
        f"prepare_env, user_class: {user_class}, user_count: {user_count}, spawn_rate: {spawn_rate}, "
        f"test_time: {test_time}, web_ui_dict: {web_ui_dict}"
    )
    env = create_env(user_class)
    env.runner.start(user_count, spawn_rate=spawn_rate)
    if web_ui_dict is not None:
        env.create_web_ui(web_ui_dict.get("host", "127.0.0.1"), web_ui_dict.get("port", 8089))
    if test_time is not None:
        gevent.spawn_later(test_time, env.runner.quit)
    env.runner.greenlet.join()
    if web_ui_dict is not None:
        env.web_ui.stop()


def create_env(user_class: [User], another_event: events = events):
    """
    :param another_event: you can use your locust event setting but don't change locust request event
    :param user_class: locust user class
    :return: locust Environment(user_class, events) events is default event
    """
    load_density_logger.info(
        f"create_env, user_class: {user_class}, another_event: {another_event}"
    )
    env = Environment(user_classes=[user_class], events=another_event)
    env.create_local_runner()
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    return env
