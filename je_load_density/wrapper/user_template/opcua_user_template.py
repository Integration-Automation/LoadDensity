"""
OPC-UA user template (asyncua, lazy import).

Each task entry::

    {"method": "connect", "url": "opc.tcp://127.0.0.1:4840/freeopcua/server/"}
    {"method": "read",  "node_id": "ns=2;i=2"}
    {"method": "write", "node_id": "ns=2;i=2", "value": 42}
    {"method": "browse", "node_id": "i=85"}
    {"method": "disconnect"}

A ``connection`` dict given to the setter supplies default step fields; keys in the step win.
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
from je_load_density.wrapper.user_template._common import (
    fire_request_event,
    new_template_event_loop,
    with_connection_defaults,
)


def set_wrapper_opcua_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("opcua_user").configure(user_detail_dict, **kwargs)
    return OpcuaUserWrapper


def _import_asyncua():
    try:
        from asyncua import Client
    except ImportError as error:
        raise RuntimeError(
            "asyncua is required for OpcuaUser; install with: pip install asyncua"
        ) from error
    return Client


class OpcuaUserWrapper(User):
    """Locust user driving asyncua calls (sync-to-async bridge)."""

    host = "opc.tcp://127.0.0.1:4840/freeopcua/server/"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._client = None
        self._loop = new_template_event_loop()

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    async def _async_connect(self, step: Dict[str, Any]) -> int:
        client_cls = _import_asyncua()
        self._client = client_cls(url=step.get("url", self.host))
        await self._client.connect()
        return 0

    async def _async_read(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("opcua not connected")
        node = self._client.get_node(step["node_id"])
        value = await node.read_value()
        return len(str(value))

    async def _async_write(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("opcua not connected")
        node = self._client.get_node(step["node_id"])
        await node.write_value(step["value"])
        return len(str(step["value"]))

    async def _async_browse(self, step: Dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("opcua not connected")
        node = self._client.get_node(step.get("node_id", "i=85"))
        children = await node.get_children()
        return len(children)

    async def _async_disconnect(self, _: Dict[str, Any]) -> int:
        if self._client is None:
            return 0
        await self._client.disconnect()
        self._client = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        mapping = {
            "connect": self._async_connect,
            "read": self._async_read,
            "write": self._async_write,
            "browse": self._async_browse,
            "disconnect": self._async_disconnect,
        }
        coro = mapping.get(method)
        if coro is None:
            return None
        return lambda step: self._run(coro(step))

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("opcua_user", parameter_resolver.resolve(raw_task))
        method = str(step.get("method", "")).lower()
        name = step.get("name") or method
        handler = self._command_for(method)
        if handler is None:
            return
        start = time.monotonic()
        try:
            length = handler(step)
            fire_request_event(self.environment, "OPC-UA", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"opcua step failed: {error!r}")
            fire_request_event(self.environment, "OPC-UA", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("opcua_user")
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
