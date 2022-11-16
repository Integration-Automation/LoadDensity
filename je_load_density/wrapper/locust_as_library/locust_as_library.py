import gevent
from locust import User
from locust import events
from locust.env import Environment
from locust.log import setup_logging
from locust.stats import stats_printer, stats_history

from je_load_density.utils.test_record.test_record_class import test_record_instance

setup_logging("INFO", None)


@events.request.add_listener
def handle_request(request_type, name, response_time, response_length, response,
                   context, exception, start_time, url, **kwargs):
    """
    handle every request event to record data
    :param request_type: default request event value
    :param name: default request event value
    :param response_time: default request event value
    :param response_length: default request event value
    :param response: default request event value
    :param context: default request event value
    :param exception: default request event value
    :param start_time: default request event value
    :param url: default request event value
    :param kwargs: catch some unknown param
    :return: None
    """
    if exception:
        test_record_instance.error_record_list.append(
            {
                "http_method": request_type,
                "test_url": url,
                "name": name,
                "status_code": response.status_code,
                "error": exception
            }
        )
    else:
        test_record_instance.test_record_list.append(
            {
                "http_method": request_type,
                "test_url": url,
                "name": name,
                "status_code": response.status_code,
                "text": response.text,
                "content": response.content,
                "headers": response.headers,
            }
        )


def create_env(user_class: [User], another_event: events = events):
    """
    :param another_event: you can use your locust event setting but don't change locust request event
    :param user_class: locust user class
    :return: locust Environment(user_class, events) events is default event
    """
    env = Environment(user_classes=[user_class], events=another_event)
    env.create_local_runner()
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    return env


def start_test(user_class: [User], user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
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
    env = create_env(user_class)
    env.runner.start(user_count, spawn_rate=spawn_rate)
    if web_ui_dict is not None:
        env.create_web_ui(web_ui_dict.get("host", "127.0.0.1"), web_ui_dict.get("port", "8089"))
    if test_time is not None:
        gevent.spawn_later(test_time, env.runner.quit)
    env.runner.greenlet.join()
    if web_ui_dict is not None:
        env.web_ui.stop()
