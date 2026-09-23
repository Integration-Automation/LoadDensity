"""
LDAP user template (ldap3, lazy import).

Each task entry::

    {"method": "connect", "host": "ldap://127.0.0.1:389",
     "user": "cn=admin,dc=ex,dc=com", "password": "secret"}
    {"method": "search", "base_dn": "dc=ex,dc=com",
     "filter": "(uid=alice)", "attributes": ["mail"]}
    {"method": "bind"}
    {"method": "unbind"}
"""

import time
from typing import Any, Callable, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_ldap_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("ldap_user").configure(user_detail_dict, **kwargs)
    return LdapUserWrapper


def _import_ldap3():
    try:
        import ldap3
    except ImportError as error:
        raise RuntimeError(
            "ldap3 is required for LdapUser; install with: pip install ldap3"
        ) from error
    return ldap3


class LdapUserWrapper(User):
    """Locust user driving ldap3 calls."""

    host = "ldap://127.0.0.1:389"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._connection = None

    def _connect(self, step: Dict[str, Any]) -> int:
        ldap3 = _import_ldap3()
        server = ldap3.Server(step.get("host", self.host))
        self._connection = ldap3.Connection(
            server,
            user=step.get("user"),
            password=step.get("password"),
            auto_bind=bool(step.get("auto_bind", True)),
        )
        return 0

    def _bind(self, _: Dict[str, Any]) -> int:
        if self._connection is None:
            raise RuntimeError("ldap not connected")
        self._connection.bind()
        return 0

    def _search(self, step: Dict[str, Any]) -> int:
        if self._connection is None:
            raise RuntimeError("ldap not connected")
        self._connection.search(
            search_base=step["base_dn"],
            search_filter=step.get("filter", "(objectClass=*)"),
            attributes=step.get("attributes"),
        )
        return sum(len(str(entry)) for entry in (self._connection.entries or []))

    def _unbind(self, _: Dict[str, Any]) -> int:
        if self._connection is None:
            return 0
        self._connection.unbind()
        self._connection = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "bind": self._bind,
            "search": self._search,
            "unbind": self._unbind,
        }.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "LDAP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"ldap step failed: {error!r}")
            fire_request_event(self.environment, "LDAP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("ldap_user")
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
