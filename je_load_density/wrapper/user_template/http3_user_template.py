"""
HTTP/3 (QUIC) user template (aioquic, lazy import).

Each task entry::

    {"method": "get",  "request_url": "https://example.com/x"}
    {"method": "post", "request_url": "https://example.com/x",
     "json": {...}, "expect_status": 201, "timeout": 5}

The step succeeds once the whole response has arrived; its length is the response body's size.
``expect_status`` fails the step on any other status. ``timeout`` (seconds, default 10) bounds
the handshake and the exchange together. ``ca_file`` adds a CA bundle to trust, for servers with
a private certificate.

aioquic is async-only; this template runs an event loop per task to keep
the dispatch contract identical to the other sync templates.

A ``connection`` dict given to the setter supplies default step fields; keys in the step win.
"""

import asyncio
import json as json_module
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

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
    run_template_coroutine,
    with_connection_defaults,
)


def set_wrapper_http3_user(user_detail_dict: Dict[str, Any], **kwargs) -> type:
    if isinstance(kwargs.get("variables"), dict):
        register_variables(kwargs["variables"])
    if isinstance(kwargs.get("csv_sources"), list):
        register_csv_sources(kwargs["csv_sources"])
    locust_wrapper_proxy.user_dict.get("http3_user").configure(user_detail_dict, **kwargs)
    return Http3UserWrapper


DEFAULT_TIMEOUT_SECONDS = 10.0


def _import_aioquic() -> SimpleNamespace:
    try:
        from aioquic.asyncio.client import connect
        from aioquic.asyncio.protocol import QuicConnectionProtocol
        from aioquic.h3.connection import H3_ALPN, H3Connection
        from aioquic.h3.events import DataReceived, HeadersReceived
        from aioquic.quic.configuration import QuicConfiguration
    except ImportError as error:
        raise RuntimeError(
            "aioquic is required for Http3User; install with: pip install aioquic"
        ) from error
    return SimpleNamespace(
        connect=connect,
        QuicConnectionProtocol=QuicConnectionProtocol,
        H3_ALPN=H3_ALPN,
        H3Connection=H3Connection,
        DataReceived=DataReceived,
        HeadersReceived=HeadersReceived,
        QuicConfiguration=QuicConfiguration,
    )


def _build_body(step: Dict[str, Any]) -> bytes:
    if "json" in step:
        return json_module.dumps(step["json"]).encode("utf-8")
    body = step.get("body", "")
    return body.encode("utf-8") if isinstance(body, str) else bytes(body)


@dataclass
class _H3Response:
    """One request's response, filled in by the protocol as HTTP/3 events arrive."""

    done: "asyncio.Future[None]"
    status: int = 0
    body: bytearray = field(default_factory=bytearray)


def _status_of(headers: List[Tuple[bytes, bytes]]) -> int:
    for name, value in headers:
        if name == b":status":
            return int(value)
    return 0


def _h3_client_protocol(aioquic: SimpleNamespace) -> type:
    """Build the client protocol class; aioquic is imported lazily, so the class is built lazily too."""

    class H3ClientProtocol(aioquic.QuicConnectionProtocol):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._http = aioquic.H3Connection(self._quic)
            self._responses: Dict[int, _H3Response] = {}

        async def request(self, headers: List[Tuple[bytes, bytes]], body: bytes) -> _H3Response:
            """Send one request and wait until its response stream ends."""
            stream_id = self._quic.get_next_available_stream_id()
            response = _H3Response(done=asyncio.get_running_loop().create_future())
            self._responses[stream_id] = response
            self._http.send_headers(stream_id, headers, end_stream=not body)
            if body:
                self._http.send_data(stream_id, body, end_stream=True)
            self.transmit()
            await response.done
            return response

        def quic_event_received(self, event: Any) -> None:
            for h3_event in self._http.handle_event(event):
                response = self._responses.get(getattr(h3_event, "stream_id", None))
                if response is None:
                    continue
                if isinstance(h3_event, aioquic.HeadersReceived):
                    response.status = response.status or _status_of(h3_event.headers)
                elif isinstance(h3_event, aioquic.DataReceived):
                    response.body.extend(h3_event.data)
                if getattr(h3_event, "stream_ended", False) and not response.done.done():
                    response.done.set_result(None)

    return H3ClientProtocol


def _request_headers(step: Dict[str, Any], method: str) -> List[Tuple[bytes, bytes]]:
    parsed = urlparse(step["request_url"])
    authority = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
    headers = [
        (b":method", method.encode()),
        (b":scheme", b"https"),
        (b":authority", authority.encode()),
        (b":path", path.encode()),
    ]
    for key, value in (step.get("headers") or {}).items():
        headers.append((key.lower().encode(), str(value).encode()))
    return headers


async def _exchange(aioquic: SimpleNamespace, step: Dict[str, Any]) -> _H3Response:
    parsed = urlparse(step["request_url"])
    method = step.get("method", "GET").upper()
    body = _build_body(step) if method in {"POST", "PUT", "PATCH"} else b""
    conf = aioquic.QuicConfiguration(alpn_protocols=aioquic.H3_ALPN, is_client=True)
    conf.verify_mode = step.get("verify_mode", conf.verify_mode)
    if step.get("ca_file"):
        conf.load_verify_locations(cafile=step["ca_file"])
    async with aioquic.connect(
        parsed.hostname, parsed.port or 443, configuration=conf, create_protocol=_h3_client_protocol(aioquic),
    ) as client:
        return await client.request(_request_headers(step, method), body)


async def _send_h3_request(step: Dict[str, Any]) -> Tuple[int, int]:
    """Send the step's request and return ``(status, response body length)``.

    Raises ``AssertionError`` when ``expect_status`` is given and the status differs, and
    ``TimeoutError`` when the handshake and exchange take longer than ``timeout`` seconds.
    """
    aioquic = _import_aioquic()
    timeout = float(step.get("timeout", DEFAULT_TIMEOUT_SECONDS))
    response = await asyncio.wait_for(_exchange(aioquic, step), timeout)
    expect = step.get("expect_status")
    if expect is not None and response.status != int(expect):
        raise AssertionError(f"http3 status expected {expect}, got {response.status}")
    return response.status, len(response.body)


class Http3UserWrapper(User):
    """Locust user driving aioquic-based HTTP/3 calls."""

    host = "https://127.0.0.1"
    wait_time = between(0.1, 0.2)

    def _do_step(self, raw_task: Dict[str, Any]) -> None:
        step = with_connection_defaults("http3_user", parameter_resolver.resolve(raw_task))
        name = step.get("name") or step.get("request_url", "")
        start = time.monotonic()
        try:
            _status, length = run_template_coroutine(_send_h3_request(step))
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
