from typing import Dict, Any

from locust import HttpUser, task, between

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_http_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 HttpUser 的代理使用者
    Configure HttpUser proxy user
    """
    locust_wrapper_proxy.user_dict.get("http_user").configure(user_detail_dict, **kwargs)
    return HttpUserWrapper


class HttpUserWrapper(HttpUser):
    """
    Locust HttpUser 包裝類別
    Locust HttpUser wrapper class
    """

    host = "http://localhost"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        # HTTP 方法映射 (HTTP method mapping)
        self.method: Dict[str, Any] = {
            "get": self.client.get,
            "post": self.client.post,
            "put": self.client.put,
            "patch": self.client.patch,
            "delete": self.client.delete,
            "head": self.client.head,
            "options": self.client.options,
        }

    @task
    def test(self) -> None:
        """
        執行測試任務
        Execute test tasks
        """
        proxy_user = locust_wrapper_proxy.user_dict.get("http_user")
        if not proxy_user or not proxy_user.tasks:
            return

        for test_task_method, test_task_data in proxy_user.tasks.items():
            http_method = self.method.get(str(test_task_method).lower())
            if http_method and isinstance(test_task_data, dict):
                request_url = test_task_data.get("request_url")
                if request_url:
                    http_method(request_url)
