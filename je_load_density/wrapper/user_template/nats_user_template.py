"""
NATS user template (nats-py, lazy import).

Each task entry::

    {"method": "connect", "servers": ["nats://127.0.0.1:4222"]}
    {"method": "publish", "subject": "topic", "payload": "hello"}
    {"method": "subscribe", "subject": "topic", "max_messages": 1, "timeout": 1.0}
    {"method": "request", "subject": "rpc", "payload": "ping", "timeout": 1.0}
    {"method": "close"}
"""

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict, Optional

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_nats_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("nats_user").configure(user_detail_dict, **kwargs)
    return NatsUserWrapper


def _import_nats():
    try:
        import nats
    except ImportError as error:
        raise RuntimeError(
            "nats-py is required for NatsUser; install with: pip install nats-py"
        ) from error
    return nats


def _payload_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")


class NatsUserWrapper(User):
    """Locust user driving nats-py calls (sync-to-async bridge)."""

    host = "nats://127.0.0.1:4222"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._loop = asyncio.new_event_loop()

    def _run(self, coro: Coroutine[Any, Any, Any]) -> Any:
        return self._loop.run_until_complete(coro)

    async def _async_connect(self, step: Dict[str, Any]) -> int:
        nats = _import_nats()
        servers = step.get("servers") or [step.get("url", self.host)]
        self._client = await nats.connect(servers)
        return 0

    async def _async_publish(self, step: Dict[str, Any]) -> int:
        payload = _payload_bytes(step.get("payload", ""))
        await self._client.publish(step["subject"], payload)
        return len(payload)

    async def _async_subscribe(self, step: Dict[str, Any]) -> int:
        sub = await self._client.subscribe(step["subject"])
        try:
            total = 0
            for _ in range(int(step.get("max_messages", 1))):
                msg = await sub.next_msg(timeout=float(step.get("timeout", 1.0)))
                total += len(msg.data)
            return total
        finally:
            await sub.unsubscribe()

    async def _async_request(self, step: Dict[str, Any]) -> int:
        payload = _payload_bytes(step.get("payload", ""))
        response = await self._client.request(
            step["subject"], payload, timeout=float(step.get("timeout", 1.0)),
        )
        return len(response.data)

    async def _async_close(self, _: Dict[str, Any]) -> int:
        if self._client is not None:
            await self._client.close()
            self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        async_map = {
            "connect": self._async_connect,
            "publish": self._async_publish,
            "subscribe": self._async_subscribe,
            "request": self._async_request,
            "close": self._async_close,
        }
        coro = async_map.get(method)
        if coro is None:
            return None
        return lambda step: self._run(coro(step))

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
            fire_request_event(self.environment, "NATS", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"nats step failed: {error!r}")
            fire_request_event(self.environment, "NATS", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("nats_user")
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
