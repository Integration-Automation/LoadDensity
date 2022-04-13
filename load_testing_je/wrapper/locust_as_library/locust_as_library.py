import gevent
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

setup_logging("INFO", None)


def create_env(user_class):
    env = Environment(user_classes=[user_class])
    env.create_local_runner()
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    return env


def start_test(user_class, user_count=1, spawn_rate=10, test_time=60):
    env = create_env(user_class)
    env.runner.start(user_count, spawn_rate=spawn_rate)
    gevent.spawn_later(test_time, lambda: env.runner.quit())
    env.runner.greenlet.join()
