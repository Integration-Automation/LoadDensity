from typing import Any, Dict

from locust import FastHttpUser, between, task

from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_db_sources,
    register_variables,
    use_resolver,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template.scenario_runner import run_scenario


def set_wrapper_fasthttp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 FastHttpUser 的代理使用者
    Configure FastHttpUser proxy user
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    if isinstance(kwargs.get("db_sources"), list):
        register_db_sources(kwargs["db_sources"])

    locust_wrapper_proxy.user_dict.get("fast_http_user").configure(user_detail_dict, **kwargs)
    return FastHttpUserWrapper


class FastHttpUserWrapper(FastHttpUser):
    """
    Locust FastHttpUser 包裝類別
    Locust FastHttpUser wrapper class
    """

    host = "http://localhost"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._parameter_resolver = parameter_resolver.fork()
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
        proxy_user = locust_wrapper_proxy.user_dict.get("fast_http_user")
        if not proxy_user or not proxy_user.tasks:
            return
        with use_resolver(self._parameter_resolver):
            run_scenario(self.method, proxy_user.tasks)
