"""
HTTP/3 (QUIC) user template (aioquic, lazy import).

Each task entry::

    {"method": "get",  "request_url": "https://example.com/x"}
    {"method": "post", "request_url": "https://example.com/x",
     "json": {...}, "expect_status": 200}

aioquic is async-only; this template runs an event loop per task to keep
the dispatch contract identical to the other sync templates.
"""

import asyncio
import json as json_module
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from locust import User, between, task

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.parameterization import (
    parameter_resolver,
    register_csv_sources,
    register_variables,
)
from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy
from je_load_density.wrapper.user_template._common import fire_request_event


def set_wrapper_http3_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("http3_user").configure(user_detail_dict, **kwargs)
    return Http3UserWrapper


def _import_aioquic():
    try:
        from aioquic.asyncio.client import connect
        from aioquic.h3.connection import H3_ALPN
        from aioquic.h3.events import DataReceived, HeadersReceived
        from aioquic.quic.configuration import QuicConfiguration
    except ImportError as error:
        raise RuntimeError(
            "aioquic is required for Http3User; install with: pip install aioquic"
        ) from error
    return connect, H3_ALPN, DataReceived, HeadersReceived, QuicConfiguration


def _build_body(step: Dict[str, Any]) -> bytes:
    if "json" in step:
        return json_module.dumps(step["json"]).encode("utf-8")
    body = step.get("body", "")
    return body.encode("utf-8") if isinstance(body, str) else bytes(body)


async def _send_h3_request(step: Dict[str, Any]) -> Tuple[int, int]:
    connect, h3_alpn, _data_received, _headers_received, configuration = _import_aioquic()
    from aioquic.h3.connection import H3Connection

    parsed = urlparse(step["request_url"])
    host = parsed.hostname
    port = parsed.port or 443
    method = step.get("method", "GET").upper()
    body = _build_body(step) if method in {"POST", "PUT", "PATCH"} else b""
    conf = configuration(alpn_protocols=h3_alpn, is_client=True)
    conf.verify_mode = step.get("verify_mode", conf.verify_mode)

    async with connect(host, port, configuration=conf) as connection:
        h3 = H3Connection(connection._quic)
        stream_id = connection._quic.get_next_available_stream_id()
        headers = [
            (b":method", method.encode()),
            (b":scheme", b"https"),
            (b":authority", host.encode()),
            (b":path", (parsed.path or "/").encode()),
        ]
        for key, value in (step.get("headers") or {}).items():
            headers.append((key.lower().encode(), str(value).encode()))
        h3.send_headers(stream_id, headers, end_stream=not body)
        if body:
            h3.send_data(stream_id, body, end_stream=True)
        await connection.wait_closed()
    return 200, len(body)


class Http3UserWrapper(User):
    """Locust user driving aioquic-based HTTP/3 calls."""

    host = "https://127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = parameter_resolver.resolve(raw_task)
        name = step.get("name") or step.get("request_url", "")
        start = time.monotonic()
        try:
            _status, length = asyncio.run(_send_h3_request(step))
            fire_request_event(self.environment, "HTTP/3", name, start, length)
        except Exception as error:
            load_density_logger.debug(f"http3 step failed: {error!r}")
            fire_request_event(self.environment, "HTTP/3", name, start, 0, error)

    @task
    def run_tasks(self) -> None:
        proxy_user = locust_wrapper_proxy.user_dict.get("http3_user")
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
