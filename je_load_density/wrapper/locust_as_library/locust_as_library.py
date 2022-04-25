import gevent
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
from locust import User
from locust import events

from je_load_density.utils.test_record.record_test_result_class import test_record

setup_logging("INFO", None)


@events.request.add_listener
def handle_request(request_type, name, response_time, response_length, response,
                   context, exception, start_time, url, **kwargs):
    # TODO
    if exception:
        test_record.error_record_list.append(
                {
                    "http_method": request_type,
                    "test_url": url,
                    "name": name,
                    "status_code": response.status_code,
                    "error": exception
                 }
        )
    else:
        test_record.record_list.append(
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


def create_env(user_class: [User]):
    env = Environment(user_classes=[user_class], events=events)
    env.create_local_runner()
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    return env


def start_test(user_class: [User], user_count: int = 50, spawn_rate: int = 10, test_time: int = 60,
               web_ui_dict: dict = None,
               **kwargs):
    env = create_env(user_class)
    env.runner.start(user_count, spawn_rate=spawn_rate)
    if web_ui_dict is not None:
        env.create_web_ui(web_ui_dict.get("host", "127.0.0.1"), web_ui_dict.get("port", "8089"))
    if test_time is not None:
        gevent.spawn_later(test_time, lambda: env.runner.quit())
    env.runner.greenlet.join()
    if web_ui_dict is not None:
        env.web_ui.stop()
