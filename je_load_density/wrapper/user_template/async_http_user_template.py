"""
Async / HTTP-2 user template.

Drives ``httpx.Client`` per user; opt-in HTTP/2 via the ``http2=True``
flag on ``start_test``. Reuses the same task schema as the FastHttp
template (method, request_url, headers, json, data, assertions, etc.).

True asyncio is incompatible with Locust's gevent loop; this template
uses the sync httpx client and runs *N* users in parallel for high
concurrency without spawning extra loops.
"""

import time
from typing import Any, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_async_http_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("async_http_user").configure(user_detail_dict, **kwargs)
    return AsyncHttpUserWrapper


_HTTPX_KWARGS = ("params", "headers", "cookies", "json", "data", "timeout", "follow_redirects")


class AsyncHttpUserWrapper(User):
    """Locust user backed by ``httpx.Client`` (HTTP/2 optional)."""

    host = "http://localhost"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import httpx
            except ImportError as error:
                raise RuntimeError(
                    "httpx is required for AsyncHttpUser; install with: pip install httpx[http2]"
                ) from error
            proxy_user = locust_wrapper_proxy.user_dict.get("async_http_user")
            http2 = bool(getattr(proxy_user, "http2", False))
            self._client = httpx.Client(http2=http2, timeout=30.0)
        return self._client

    @staticmethod
    def _request_kwargs(step: Dict[str, Any]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        for key in _HTTPX_KWARGS:
            if key in step and step[key] is not None:
                kwargs[key] = step[key]
        if step.get("allow_redirects") is not None and "follow_redirects" not in kwargs:
            kwargs["follow_redirects"] = bool(step["allow_redirects"])
        return kwargs

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="HTTPX",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=name,
            response=None,
            start_time=start,
        )

    def _check_assertions(self, response, step: Dict[str, Any]) -> Optional[str]:
        for assertion in step.get("assertions") or []:
            kind = str(assertion.get("type", "")).lower()
            if kind == "status_code":
                if int(response.status_code) != int(assertion.get("value")):
                    return f"status_code expected {assertion.get('value')}, got {response.status_code}"
            elif kind == "contains":
                if str(assertion.get("value")) not in (response.text or ""):
                    return f"body does not contain {assertion.get('value')!r}"
        return None

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "")).lower()
        url = step.get("request_url") or step.get("url")
        if not method or not url:
            return
        name = step.get("name") or url
        start = time.monotonic()
        try:
            client = self._ensure_client()
            response = client.request(method.upper(), url,
                                       **self._request_kwargs(step))
            failure = self._check_assertions(response, step)
            length = len(response.content or b"")
            if failure is not None:
                self._fire(name, start, length, AssertionError(failure))
            else:
                self._fire(name, start, length)
        except Exception as error:
            load_density_logger.debug(f"async_http step failed: {error!r}")
            self._fire(name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("async_http_user")
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
