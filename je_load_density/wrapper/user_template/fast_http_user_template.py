from locust import FastHttpUser
from locust import task

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_fasthttp_user(user_detail_dict, **kwargs):
    locust_wrapper_proxy.user_dict.get("fast_http_user").setting(user_detail_dict, **kwargs)
    return FastHttpUserWrapper


class FastHttpUserWrapper(FastHttpUser):
    """
    locust fast http user use to test
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
        for test_task_method, test_task_data in locust_wrapper_proxy.user_dict.get("fast_http_user").tasks.items():
            self.method.get(test_task_method)(test_task_data.get("request_url"))