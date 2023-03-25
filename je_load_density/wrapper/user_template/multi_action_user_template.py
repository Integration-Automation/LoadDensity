from locust import FastHttpUser, task

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_sequence_user(user_detail_dict: dict, tasks: dict):
    locust_wrapper_proxy.user_dict.get("multi_action_user").setting(user_detail_dict, tasks)
    return MultiActionUserWrapper


class MultiActionUserWrapper(FastHttpUser):
    """
    locust httpuser use to test
    """
    host = "http://localhost"
    min_wait = 5
    max_wait = 20

    def __init__(self, environment):
        super().__init__(environment)
        self.method = {
            "get": self.client.get,
            "post": self.client.post,
            "put": self.client.put,
            "patch": self.client.patch,
            "delete": self.client.delete,
            "head": self.client.head,
            "options": self.client.options,
        }

    @task
    def test(self):
        for test_task_method, test_task_data in locust_wrapper_proxy.user_dict.get("multi_action_user").tasks.items():
            self.method.get(test_task_method)(test_task_data.get("request_url"))


