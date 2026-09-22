"""
IMAP user template (stdlib imaplib).

Each task entry::

    {"method": "connect", "host": "imap.example.com", "port": 993, "ssl": true}
    {"method": "login", "username": "u", "password": "p"}
    {"method": "select", "mailbox": "INBOX"}
    {"method": "search", "criteria": "ALL"}
    {"method": "fetch", "msg_id": "1", "spec": "(RFC822)"}
    {"method": "logout"}
"""

import imaplib
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
from je_load_density.wrapper.user_template._common import (
    coerce_response_length,
    fire_request_event,
)


def set_wrapper_imap_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("imap_user").configure(user_detail_dict, **kwargs)
    return ImapUserWrapper


class ImapUserWrapper(User):
    """Locust user driving imaplib calls."""

    host = "imap.example.com"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client: Optional[imaplib.IMAP4] = None

    def _connect(self, step: Dict[str, Any]) -> Any:
        host = step.get("host", "127.0.0.1")
        port = int(step.get("port", 143))
        use_ssl = bool(step.get("ssl", False))
        if use_ssl:
            self._client = imaplib.IMAP4_SSL(host, port)
        else:
            self._client = imaplib.IMAP4(host, port)
        return self._client.noop()

    def _login(self, step: Dict[str, Any]) -> Any:
        if self._client is None:
            raise RuntimeError("imap client not connected")
        return self._client.login(step.get("username", ""), step.get("password", ""))

    def _select(self, step: Dict[str, Any]) -> Any:
        if self._client is None:
            raise RuntimeError("imap client not connected")
        return self._client.select(step.get("mailbox", "INBOX"))

    def _search(self, step: Dict[str, Any]) -> Any:
        if self._client is None:
            raise RuntimeError("imap client not connected")
        return self._client.search(None, step.get("criteria", "ALL"))

    def _fetch(self, step: Dict[str, Any]) -> Any:
        if self._client is None:
            raise RuntimeError("imap client not connected")
        return self._client.fetch(str(step.get("msg_id", "1")), step.get("spec", "(RFC822)"))

    def _logout(self, _: Dict[str, Any]) -> Any:
        if self._client is None:
            return None
        try:
            return self._client.logout()
        finally:
            self._client = None

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
        return {
            "connect": self._connect,
            "login": self._login,
            "select": self._select,
            "search": self._search,
            "fetch": self._fetch,
            "logout": self._logout,
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
            result = handler(step)
            fire_request_event(
                self.environment, "IMAP", name, start, coerce_response_length(result),
            )
        except Exception as error:
            load_density_logger.debug(f"imap step failed: {error!r}")
            fire_request_event(self.environment, "IMAP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("imap_user")
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
