from typing import Any, Dict

from locust import HttpUser, between, task

from je_load_density.utils.parameterization import (
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template.scenario_runner import run_scenario


def set_wrapper_http_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 HttpUser 的代理使用者
    Configure HttpUser proxy user
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])

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
        proxy_user = locust_wrapper_proxy.user_dict.get("http_user")
        if not proxy_user or not proxy_user.tasks:
            return
        run_scenario(self.method, proxy_user.tasks)
