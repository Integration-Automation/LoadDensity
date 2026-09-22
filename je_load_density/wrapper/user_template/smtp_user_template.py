"""
SMTP user template (stdlib smtplib).

Each task entry::

    {"method": "connect", "host": "smtp.example.com", "port": 587, "tls": true}
    {"method": "login", "username": "u", "password": "p"}
    {"method": "send", "from": "a@x", "to": ["b@y"], "subject": "hi", "body": "..."}
    {"method": "quit"}
"""

import smtplib
import time
from email.message import EmailMessage
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


def set_wrapper_smtp_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("smtp_user").configure(user_detail_dict, **kwargs)
    return SmtpUserWrapper


def _build_message(step: Dict[str, Any]) -> EmailMessage:
    message = EmailMessage()
    message["From"] = step.get("from", "")
    to_value = step.get("to", [])
    if isinstance(to_value, list):
        message["To"] = ", ".join(to_value)
    else:
        message["To"] = str(to_value)
    message["Subject"] = step.get("subject", "")
    message.set_content(step.get("body", ""))
    return message


class SmtpUserWrapper(User):
    """Locust user driving smtplib calls."""

    host = "smtp.example.com"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client: Optional[smtplib.SMTP] = None

    def _connect(self, step: Dict[str, Any]) -> Any:
        host = step.get("host", "127.0.0.1")
        port = int(step.get("port", 25))
        timeout = float(step.get("timeout", 10))
        use_ssl = bool(step.get("ssl", False))
        if use_ssl:
            self._client = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            self._client = smtplib.SMTP(host, port, timeout=timeout)
            if step.get("tls"):
                self._client.starttls()
        return self._client.noop()

    def _login(self, step: Dict[str, Any]) -> Any:
        if self._client is None:
            raise RuntimeError("smtp client not connected")
        return self._client.login(step.get("username", ""), step.get("password", ""))

    def _send(self, step: Dict[str, Any]) -> bytes:
        """Send the message and return its bytes, whose length is the step's response length."""
        if self._client is None:
            raise RuntimeError("smtp client not connected")
        message = _build_message(step)
        self._client.send_message(message)
        return message.as_bytes()

    def _quit(self, _: Dict[str, Any]) -> Any:
        if self._client is None:
            return None
        result = self._client.quit()
        self._client = None
        return result

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
        return {
            "connect": self._connect,
            "login": self._login,
            "send": self._send,
            "quit": self._quit,
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
                self.environment, "SMTP", name, start, coerce_response_length(result),
            )
        except Exception as error:
            load_density_logger.debug(f"smtp step failed: {error!r}")
            fire_request_event(self.environment, "SMTP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("smtp_user")
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
