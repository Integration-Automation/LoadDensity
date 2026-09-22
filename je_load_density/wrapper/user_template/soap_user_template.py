"""
SOAP user template (urllib + stdlib XML, no extra deps).

Each task entry::

    {"method": "call", "endpoint": "https://svc/SoapEndpoint",
     "action": "urn:DoStuff",
     "envelope": "<soap:Envelope ...>...</soap:Envelope>",
     "expect_contains": "ResponseTag"}
"""

import time
import urllib.request
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


def set_wrapper_soap_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("soap_user").configure(user_detail_dict, **kwargs)
    return SoapUserWrapper


def _call(step: Dict[str, Any]) -> int:
    body = step.get("envelope", "")
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers = {
        "Content-Type": step.get("content_type", "text/xml; charset=utf-8"),
        "SOAPAction": step.get("action", ""),
    }
    for key, value in (step.get("headers") or {}).items():
        headers[str(key)] = str(value)
    request = urllib.request.Request(
        step["endpoint"], data=body, headers=headers, method="POST",
    )
    timeout = float(step.get("timeout", 10.0))
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        payload = response.read()
    expect = step.get("expect_contains")
    if expect and expect not in payload.decode("utf-8", errors="replace"):
        raise AssertionError(f"soap response missing {expect!r}")
    return len(payload)


class SoapUserWrapper(User):
    """Locust user driving raw SOAP envelopes over HTTP."""

    host = "https://127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {"call": _call}.get(method)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "call")).lower()
        name = step.get("name") or step.get("action") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "SOAP", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"soap step failed: {error!r}")
            fire_request_event(self.environment, "SOAP", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("soap_user")
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
