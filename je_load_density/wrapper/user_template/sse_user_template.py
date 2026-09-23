"""
Server-Sent Events (SSE) user template.

Each task entry should look like::

    {"method": "open",   "request_url": "https://api/stream"}
    {"method": "wait",   "expect": "ready", "timeout": 5}
    {"method": "close"}

Uses ``requests`` with streaming for the SSE GET, which is already in
the base dependency tree. ``host`` given to ``set_wrapper_sse_user`` is the
URL used until a step names one.
"""

import time
from typing import Any, Dict, Iterator, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import default_host


def set_wrapper_sse_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("sse_user").configure(user_detail_dict, **kwargs)
    return SseUserWrapper


def _parse_sse_lines(lines: Iterator[str]) -> Iterator[Dict[str, str]]:
    event: Dict[str, str] = {}
    for line in lines:
        if not line:
            if event:
                yield event
                event = {}
            continue
        if ":" not in line:
            event[line] = ""
            continue
        key, _, value = line.partition(":")
        event[key.strip()] = value.lstrip()


class SseUserWrapper(User):
    """Locust SSE user wrapper."""

    host = "http://localhost"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._response = None
        self._url: str = ""

    def _open(self, url: str, timeout: float, headers: Optional[Dict[str, str]]) -> None:
        import requests
        merged = dict(headers or {})
        merged.setdefault("Accept", "text/event-stream")
        self._response = requests.get(url, headers=merged, stream=True, timeout=timeout)
        self._url = url

    def _close(self) -> None:
        if self._response is not None:
            try:
                self._response.close()
            except Exception as error:
                load_density_logger.debug(f"sse close failed: {error!r}")
            self._response = None

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="SSE",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=self._url,
            response=None,
            start_time=start,
        )

    def _wait_for(self, expect: Optional[str], timeout: float) -> int:
        if self._response is None:
            raise RuntimeError("SSE stream not open")
        deadline = time.monotonic() + timeout
        total = 0
        for event in _parse_sse_lines(self._response.iter_lines(decode_unicode=True)):
            total += sum(len(v) for v in event.values())
            if expect is None or expect in event.get("data", ""):
                return total
            if time.monotonic() > deadline:
                raise TimeoutError(f"SSE waited > {timeout}s for {expect!r}")
        raise RuntimeError("SSE stream ended before expected event")

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "wait")).lower()
        url = step.get("request_url") or step.get("url") or self._url or default_host("sse_user", "")
        name = step.get("name") or url or method
        timeout = float(step.get("timeout", 30))
        start = time.monotonic()
        try:
            length = self._dispatch(method, url, timeout, step)
            self._fire(name, start, length)
        except Exception as error:
            self._fire(name, start, 0, error)

    def _dispatch(self, method: str, url: str, timeout: float, step: Dict[str, Any]) -> int:
        if method in {"open", "connect"}:
            self._open(url, timeout, step.get("headers"))
            return 0
        if method == "close":
            self._close()
            return 0
        if method == "wait":
            return self._wait_for(step.get("expect"), timeout)
        raise ValueError(f"unsupported sse method: {method}")

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("sse_user")
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
