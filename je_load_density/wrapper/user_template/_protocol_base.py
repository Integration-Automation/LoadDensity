"""
Reusable Locust User base for protocol templates.

Subclasses provide ``_proxy_key``, ``_request_type``, and a
``_command_for(method)`` implementation. The base handles parameter
resolution, dispatch, Locust event firing, and the run-task loop. A
``connection`` dict given to the setter supplies default step fields.
"""

import time
from typing import Any, Callable, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import parameter_resolver
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import (
    fire_request_event,
    with_connection_defaults,
)


class ProtocolUserBase(User):
    """Common base for the new wave of protocol user templates."""

    abstract = True
    _proxy_key: str = ""
    _request_type: str = "GENERIC"
    host = "127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        raise NotImplementedError

    def _step_name(self, step: Dict[str, Any]) -> str:
        return str(step.get("name") or step.get("method", "") or "")

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults(self._proxy_key, parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        handler = self._command_for(method)
        if handler is None:
            return
        name = self._step_name(step)
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, self._request_type, name, start, length)
        except Exception as error:
            load_density_logger.debug(
                f"{self._request_type} step failed: {error!r}"
            )
            fire_request_event(self.environment, self._request_type, name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get(self._proxy_key)
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


def make_setter(proxy_key: str, user_cls: type) -> Callable[..., type]:
    """Build a ``set_wrapper_*`` factory for the named proxy key."""
    from je_load_density.utils.parameterization import (
        register_csv_sources,
        register_variables,
    )

    def _setter(user_detail_dict: Dict[str, Any], **kwargs) -> type:
        if isinstance(kwargs.get("variables"), dict):
            register_variables(kwargs["variables"])
        if isinstance(kwargs.get("csv_sources"), list):
            register_csv_sources(kwargs["csv_sources"])
        locust_wrapper_proxy.user_dict.get(proxy_key).configure(user_detail_dict, **kwargs)
        return user_cls

    return _setter
