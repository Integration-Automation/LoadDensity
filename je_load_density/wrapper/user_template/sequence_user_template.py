from locust import FastHttpUser, task

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_sequence_user(user_detail_dict: dict, tasks: [list, dict]):
    locust_wrapper_proxy.user_dict.get("sequence_user").setting(user_detail_dict, tasks)
    return SequenceUserWrapper


class SequenceUserWrapper(FastHttpUser):
    """
    locust httpuser use to test
    """
    host = "http://localhost"
    min_wait = 5
    max_wait = 20

    def __init__(self, environment):
        super().__init__(environment)

    @task
    def aa(self):
        print(locust_wrapper_proxy.user_dict.get("sequence_user").tasks)
