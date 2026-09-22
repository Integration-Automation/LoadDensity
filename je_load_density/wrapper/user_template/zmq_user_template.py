"""
ZeroMQ user template (pyzmq, lazy import).

Each task entry::

    {"method": "connect", "socket_type": "REQ", "endpoint": "tcp://127.0.0.1:5555"}
    {"method": "send", "payload": "hello"}
    {"method": "recv", "timeout_ms": 1000}
    {"method": "subscribe", "topic": "news"}
    {"method": "close"}
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


def set_wrapper_zmq_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("zmq_user").configure(user_detail_dict, **kwargs)
    return ZmqUserWrapper


def _import_zmq():
    try:
        import zmq
    except ImportError as error:
        raise RuntimeError(
            "pyzmq is required for ZmqUser; install with: pip install pyzmq"
        ) from error
    return zmq


def _bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode("utf-8")


class ZmqUserWrapper(User):
    """Locust user driving pyzmq sockets."""

    host = "tcp://127.0.0.1:5555"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._context = None
        self._socket = None

    def _connect(self, step: Dict[str, Any]) -> int:
        zmq = _import_zmq()
        socket_type = getattr(zmq, step.get("socket_type", "REQ"))
        self._context = zmq.Context.instance()
        self._socket = self._context.socket(socket_type)
        if bool(step.get("bind", False)):
            self._socket.bind(step.get("endpoint", self.host))
        else:
            self._socket.connect(step.get("endpoint", self.host))
        return 0

    def _send(self, step: Dict[str, Any]) -> int:
        if self._socket is None:
            raise RuntimeError("zmq socket not open")
        payload = _bytes(step.get("payload", ""))
        self._socket.send(payload)
        return len(payload)

    def _recv(self, step: Dict[str, Any]) -> int:
        if self._socket is None:
            raise RuntimeError("zmq socket not open")
        zmq = _import_zmq()
        timeout = int(step.get("timeout_ms", 1000))
        if self._socket.poll(timeout, zmq.POLLIN) == 0:
            raise TimeoutError("zmq recv timeout")
        data = self._socket.recv()
        return len(data)

    def _subscribe(self, step: Dict[str, Any]) -> int:
        if self._socket is None:
            raise RuntimeError("zmq socket not open")
        zmq = _import_zmq()
        self._socket.setsockopt(zmq.SUBSCRIBE, _bytes(step.get("topic", "")))
        return 0

    def _close(self, _: Dict[str, Any]) -> int:
        if self._socket is not None:
            self._socket.close(linger=0)
            self._socket = None
        self._context = None
        return 0

    def _command_for(self, method: str) -> Optional[Callable[[Dict[str, Any]], int]]:
        return {
            "connect": self._connect,
            "send": self._send,
            "recv": self._recv,
            "subscribe": self._subscribe,
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
            fire_request_event(self.environment, "ZMQ", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"zmq step failed: {error!r}")
            fire_request_event(self.environment, "ZMQ", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("zmq_user")
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
