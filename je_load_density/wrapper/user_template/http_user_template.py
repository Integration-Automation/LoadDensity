from locust import HttpUser, task

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_http_user(user_detail_dict: dict, **kwargs):
    locust_wrapper_proxy.user_dict.get("http_user").setting(user_detail_dict, **kwargs)
    return HttpUserWrapper


class HttpUserWrapper(HttpUser):
    """
    locust http user use to test
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
        for test_task_method, test_task_data in locust_wrapper_proxy.user_dict.get("http_user").tasks.items():
            self.method.get(test_task_method)(test_task_data.get("request_url"))


