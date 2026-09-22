"""
GraphQL WebSocket subscription user template (websocket-client, lazy import).

Implements the ``graphql-transport-ws`` protocol::

    {"method": "connect", "url": "wss://api/graphql", "protocol": "graphql-transport-ws"}
    {"method": "subscribe", "id": "1", "query": "subscription { x }",
     "variables": {}, "max_messages": 1, "timeout": 5.0}
    {"method": "complete", "id": "1"}
    {"method": "close"}
"""

import json as json_module
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


def set_wrapper_graphql_ws_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("graphql_ws_user").configure(user_detail_dict, **kwargs)
    return GraphQLWebSocketUserWrapper


def _import_websocket():
    try:
        import websocket
    except ImportError as error:
        raise RuntimeError(
            "websocket-client is required for GraphQLWebSocketUser; "
            "install with: pip install websocket-client"
        ) from error
    return websocket


class GraphQLWebSocketUserWrapper(User):
    """Locust user driving graphql-transport-ws subscriptions."""

    host = "wss://127.0.0.1/graphql"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._ws = None

    def _connect(self, step: Dict[str, Any]) -> int:
        websocket_mod = _import_websocket()
        protocol = step.get("protocol", "graphql-transport-ws")
        self._ws = websocket_mod.create_connection(
            step.get("url", self.host),
            subprotocols=[protocol],
            timeout=float(step.get("timeout", 5.0)),
            header=step.get("headers"),
        )
        init_payload = {"type": "connection_init", "payload": step.get("init_payload", {})}
        self._ws.send(json_module.dumps(init_payload))
        ack = self._ws.recv()
        return len(ack or "")

    def _subscribe(self, step: Dict[str, Any]) -> int:
        if self._ws is None:
            raise RuntimeError("graphql-ws not connected")
        sub_id = str(step.get("id", "1"))
        payload = {
            "id": sub_id,
            "type": "subscribe",
            "payload": {
                "query": step["query"],
                "variables": step.get("variables", {}),
                "operationName": step.get("operation_name"),
            },
        }
        self._ws.send(json_module.dumps(payload))
        total = 0
        timeout = float(step.get("timeout", 5.0))
        self._ws.settimeout(timeout)
        for _ in range(int(step.get("max_messages", 1))):
            data = self._ws.recv()
            if not data:
                break
            total += len(data)
            try:
                parsed = json_module.loads(data)
            except json_module.JSONDecodeError:
                continue
            if parsed.get("type") == "complete":
                break
        return total

    def _complete(self, step: Dict[str, Any]) -> int:
        if self._ws is None:
            return 0
        message = json_module.dumps({"id": str(step.get("id", "1")), "type": "complete"})
        self._ws.send(message)
        return len(message)

    def _close(self, _: Dict[str, Any]) -> int:
        if self._ws is None:
            return 0
        try:
            self._ws.close()
        finally:
            self._ws = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "subscribe": self._subscribe,
            "complete": self._complete,
            "close": self._close,
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
            fire_request_event(self.environment, "GRAPHQL-WS", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"graphql-ws step failed: {error!r}")
            fire_request_event(self.environment, "GRAPHQL-WS", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("graphql_ws_user")
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
