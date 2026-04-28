import time
from typing import Any, Dict

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy


def set_wrapper_websocket_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 WebSocket User 的代理使用者
    Configure WebSocket User proxy
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])

    locust_wrapper_proxy.user_dict.get("websocket_user").configure(user_detail_dict, **kwargs)
    return WebSocketUserWrapper


class WebSocketUserWrapper(User):
    """
    Locust WebSocket User 包裝類別
    Locust WebSocket User wrapper class

    Each task entry should look like::

        {
            "method": "send",          # send | recv | sendrecv | connect | close
            "request_url": "ws://...", # required for connect; otherwise reused
            "name": "login",           # event name; defaults to URL
            "payload": "...",
            "expect": "substring",     # optional substring assertion on recv
            "timeout": 5
        }
    """

    host = "ws://localhost"
    wait_time = between(0.1, 0.2)

    def __init__(self, environment):
        super().__init__(environment)
        self._ws = None
        self._url: str = ""

    def _ensure_websocket(self):
        if self._ws is None:
            try:
                from websocket import create_connection
            except ImportError as error:
                raise RuntimeError("websocket-client is required for WebSocketUser") from error
            self._create_connection = create_connection
        return self._create_connection

    def _connect(self, url: str, timeout: float) -> None:
        create_connection = self._ensure_websocket()
        if self._ws is not None and self._url == url:
            return
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception as error:
                load_density_logger.debug(f"websocket close before reconnect failed: {error!r}")
        self._ws = create_connection(url, timeout=timeout)
        self._url = url

    def _fire(self, name: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type="WS",
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=self._url,
            response=None,
            start_time=start,
        )

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        method = str(step.get("method", "send")).lower()
        url = step.get("request_url") or step.get("url") or self._url
        name = step.get("name") or url or method
        timeout = float(step.get("timeout", 5))

        start = time.monotonic()
        try:
            length = self._dispatch_step(method, url, timeout, step)
            self._fire(name, start, length)
        except Exception as error:
            self._fire(name, start, 0, error)

    def _dispatch_step(self, method: str, url: str, timeout: float, step: Dict[str, Any]) -> int:
        if method == "connect":
            self._connect(url, timeout)
            return 0
        if method == "close":
            self._close_socket()
            return 0

        if self._ws is None and url:
            self._connect(url, timeout)
        if self._ws is None:
            raise RuntimeError("websocket connection not established")

        if method == "send":
            return self._send_only(step)
        if method == "recv":
            return self._recv_only(timeout, step)
        if method == "sendrecv":
            return self._send_then_recv(timeout, step)
        raise ValueError(f"unsupported websocket method: {method}")

    def _close_socket(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def _send_only(self, step: Dict[str, Any]) -> int:
        payload = step.get("payload", "")
        self._ws.send(payload)
        return len(payload)

    def _recv_only(self, timeout: float, step: Dict[str, Any]) -> int:
        self._ws.settimeout(timeout)
        data = self._ws.recv()
        _verify_expect(data, step.get("expect"))
        return len(data) if data else 0

    def _send_then_recv(self, timeout: float, step: Dict[str, Any]) -> int:
        payload = step.get("payload", "")
        self._ws.send(payload)
        self._ws.settimeout(timeout)
        data = self._ws.recv()
        _verify_expect(data, step.get("expect"))
        return len(payload) + (len(data) if data else 0)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("websocket_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            load_density_logger.warning("websocket_user.tasks must be a list")
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)


def _verify_expect(data: Any, expect: Any) -> None:
    if expect is None:
        return
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = str(data)
    if str(expect) not in text:
        raise AssertionError(f"expected {expect!r} in response")
