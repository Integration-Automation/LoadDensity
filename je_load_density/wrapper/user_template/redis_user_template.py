"""
Redis user template.

Each task entry::

    {"method": "set", "key": "k", "value": "v"}
    {"method": "get", "key": "k", "expect": "v"}
    {"method": "incr", "key": "counter"}
    {"method": "lpush", "key": "q", "value": "x"}
    {"method": "rpop", "key": "q"}
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


def set_wrapper_redis_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("redis_user").configure(user_detail_dict, **kwargs)
    return RedisUserWrapper


class RedisUserWrapper(User):
    """Locust user that exercises a Redis instance via redis-py."""

    host = "redis://127.0.0.1:6379/0"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                import redis
            except ImportError as error:
                raise RuntimeError(
                    "redis is required for RedisUser; install with: pip install redis"
                ) from error
            proxy_user = locust_wrapper_proxy.user_dict.get("redis_user")
            conn = (getattr(proxy_user, "connection", None) or {})
            url = conn.get("url") or self.host
            self._client = redis.Redis.from_url(url)
        return self._client

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="REDIS",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=name,
            response=None,
            start_time=start,
        )

    def _coerce(self, value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, (bytes, str)):
            return len(value)
        return 1

    def _verify_expect(self, value: Any, expect: Any) -> None:
        if expect is None:
            return
        if isinstance(value, bytes):
            text = value.decode("utf-8", errors="replace")
        else:
            text = "" if value is None else str(value)
        if str(expect) != text:
            raise AssertionError(f"redis expected {expect!r}, got {text!r}")

    def _command_for(self, method: str) -> Optional[Callable[..., Any]]:
        # The client is created inside each command, so a missing redis package or a bad URL
        # happens inside _do_step's try and is reported as a failed request.
        return {
            "get":   lambda step: self._ensure_client().get(step["key"]),
            "set":   lambda step: self._ensure_client().set(step["key"], step.get("value", "")),
            "incr":  lambda step: self._ensure_client().incr(step["key"]),
            "lpush": lambda step: self._ensure_client().lpush(step["key"], step.get("value", "")),
            "rpop":  lambda step: self._ensure_client().rpop(step["key"]),
            "delete": lambda step: self._ensure_client().delete(step["key"]),
            "exists": lambda step: self._ensure_client().exists(step["key"]),
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
            self._verify_expect(result, step.get("expect"))
            self._fire(name, start, self._coerce(result))
        except Exception as error:
            load_density_logger.debug(f"redis step failed: {error!r}")
            self._fire(name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("redis_user")
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
