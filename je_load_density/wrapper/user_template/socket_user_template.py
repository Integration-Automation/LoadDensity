import socket
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


def set_wrapper_socket_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    """
    設定 Socket User 的代理使用者 (TCP/UDP)
    Configure raw socket User proxy
    """
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])

    locust_wrapper_proxy.user_dict.get("socket_user").configure(user_detail_dict, **kwargs)
    return SocketUserWrapper


class SocketUserWrapper(User):
    """
    Locust 原生 Socket User 包裝類別 (TCP/UDP)
    Raw socket Locust user (TCP/UDP).

    Each task entry should look like::

        {
            "protocol": "tcp",          # tcp | udp
            "target": "127.0.0.1:9000",
            "payload": "...",           # str or hex string with prefix "hex:"
            "expect_bytes": 64,         # bytes to read; 0 to skip read
            "expect_substring": "OK",   # optional substring assertion
            "timeout": 5,
            "name": "ping"
        }
    """

    host = "127.0.0.1:9000"
    wait_time = between(0.1, 0.2)

    def _fire(self, name: str, target: str, protocol: str, start: float, length: int, exception: Exception = None) -> None:
        self.environment.events.request.fire(
            request_type=protocol.upper(),
            name=name,
            response_time=(time.monotonic() - start) * 1000,
            response_length=length,
            exception=exception,
            context={},
            url=target,
            response=None,
            start_time=start,
        )

    @staticmethod
    def _to_bytes(value: Any) -> bytes:
        if isinstance(value, bytes):
            return value
        text = str(value or "")
        if text.startswith("hex:"):
            return bytes.fromhex(text[4:])
        return text.encode("utf-8")

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        protocol = str(step.get("protocol", "tcp")).lower()
        target = step.get("target") or step.get("host") or self.host
        host, _, port = target.partition(":")
        port = int(port or 0)
        timeout = float(step.get("timeout", 5))
        payload = self._to_bytes(step.get("payload", ""))
        expect_bytes = int(step.get("expect_bytes", 0))
        expect_substring = step.get("expect_substring")
        name = step.get("name") or f"{protocol}:{target}"

        start = time.monotonic()
        try:
            if protocol == "tcp":
                length = self._do_tcp(host, port, payload, expect_bytes, expect_substring, timeout)
            elif protocol == "udp":
                length = self._do_udp(host, port, payload, expect_bytes, expect_substring, timeout)
            else:
                raise ValueError(f"unsupported protocol: {protocol}")
            self._fire(name, target, protocol, start, length)
        except Exception as error:
            self._fire(name, target, protocol, start, 0, error)

    @staticmethod
    def _do_tcp(host: str, port: int, payload: bytes, expect_bytes: int, expect_substring: Any, timeout: float) -> int:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(payload)
            data = b""
            if expect_bytes > 0:
                sock.settimeout(timeout)
                while len(data) < expect_bytes:
                    chunk = sock.recv(expect_bytes - len(data))
                    if not chunk:
                        break
                    data += chunk
            _verify_substring(data, expect_substring)
            return len(payload) + len(data)

    @staticmethod
    def _do_udp(host: str, port: int, payload: bytes, expect_bytes: int, expect_substring: Any, timeout: float) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(payload, (host, port))
            data = b""
            if expect_bytes > 0:
                data, _ = sock.recvfrom(max(expect_bytes, 1))
            _verify_substring(data, expect_substring)
            return len(payload) + len(data)
        finally:
            sock.close()

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("socket_user")
        if not proxy_user or not proxy_user.tasks:
            return
        tasks = proxy_user.tasks
        if isinstance(tasks, dict) and "tasks" in tasks:
            tasks = tasks.get("tasks") or []
        if not isinstance(tasks, list):
            load_density_logger.warning("socket_user.tasks must be a list")
            return
        for raw_task in tasks:
            if isinstance(raw_task, dict):
                self._do_step(raw_task)


def _verify_substring(data: bytes, expect: Any) -> None:
    if expect is None:
        return
    text = data.decode("utf-8", errors="replace")
    if str(expect) not in text:
        raise AssertionError(f"expected {expect!r} in response")
