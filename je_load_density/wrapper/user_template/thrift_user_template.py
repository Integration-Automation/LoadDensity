"""
Apache Thrift user template (thriftpy2, lazy import).

Each task entry::

    {"method": "connect", "host": "127.0.0.1", "port": 9090,
     "thrift_file": "calc.thrift", "service": "Calculator"}
    {"method": "call", "function": "add", "args": [1, 2]}
    {"method": "close"}

``thrift_file`` is parsed via ``thriftpy2.load`` so no codegen step is
required.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_thrift_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("thrift_user").configure(user_detail_dict, **kwargs)
    return ThriftUserWrapper


def _import_thriftpy():
    try:
        import thriftpy2
        from thriftpy2.rpc import make_client
    except ImportError as error:
        raise RuntimeError(
            "thriftpy2 is required for ThriftUser; install with: pip install thriftpy2"
        ) from error
    return thriftpy2, make_client


class ThriftUserWrapper(User):
    """Locust user driving thriftpy2 RPC calls."""

    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _connect(self, step: Dict[str, Any]) -> int:
        thriftpy2, make_client = _import_thriftpy()
        module = thriftpy2.load(step["thrift_file"])
        service = getattr(module, step["service"])
        self._client = make_client(
            service,
            host=step.get("host", self.host),
            port=int(step.get("port", 9090)),
        )
        return 0

    def _call(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("thrift not connected")
        function = getattr(self._client, step["function"])
        args: List[Any] = step.get("args") or []
        kwargs: Dict[str, Any] = step.get("kwargs") or {}
        result = function(*args, **kwargs)
        return len(str(result))

    def _close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"connect": self._connect, "call": self._call, "close": self._close}.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or step.get("function") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "THRIFT", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"thrift step failed: {error!r}")
            fire_request_event(self.environment, "THRIFT", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("thrift_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)
