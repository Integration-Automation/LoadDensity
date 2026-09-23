"""
Shared helpers for protocol user templates.

Centralises the Locust ``request`` event firing pattern so every new
template (SMTP, IMAP, FTP, AMQP, NATS, etc.) avoids duplicating the same
event-dispatch boilerplate.
"""

import asyncio
import json
import socket
import time
from typing import Any, Coroutine, Dict, Optional, TypeVar

from je_load_density.wrapper.proxy.proxy_user import locust_wrapper_proxy

T = TypeVar("T")


async def _getaddrinfo_inline(host: Any, port: Any, *, family: int = 0, type: int = 0,  # noqa: A002
                              proto: int = 0, flags: int = 0) -> list:
    """``loop.getaddrinfo`` resolved in the calling thread instead of the loop's thread pool."""
    return socket.getaddrinfo(host, port, family, type, proto, flags)


def new_template_event_loop() -> asyncio.AbstractEventLoop:
    """Return a new event loop for a template that drives an asyncio client from a Locust user.

    The loop's ``getaddrinfo`` resolves in the calling thread, not in the loop's thread pool.
    Under Locust, gevent turns the pool's threads into greenlets, and on Windows they never run
    while the loop waits on IOCP, so a host name lookup through the pool never returns. The
    inline lookup is cooperative under gevent and an ordinary blocking call without it.
    """
    loop = asyncio.new_event_loop()
    loop.getaddrinfo = _getaddrinfo_inline  # type: ignore[method-assign]
    return loop


def run_template_coroutine(coro: Coroutine[Any, Any, T]) -> T:
    """Run ``coro`` to completion on a fresh :func:`new_template_event_loop` loop, like ``asyncio.run``.

    The loop is the thread's current event loop while it runs. Tasks still pending when ``coro``
    finishes are cancelled, and the loop is closed.
    """
    loop = new_template_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for leftover in pending:
                leftover.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def fire_request_event(
    environment: Any,
    request_type: str,
    name: str,
    start: float,
    response_length: int = 0,
    exception: Optional[BaseException] = None,
) -> None:
    """Fire a Locust ``request`` event with consistent shape."""
    environment.events.request.fire(
        request_type=request_type,
        name=name,
        response_time=(time.monotonic() - start) * 1000,
        response_length=response_length,
        exception=exception,
        context={},
        url=name,
        response=None,
        start_time=start,
    )


def default_host(proxy_key: str, fallback: Any) -> Any:
    """Return the ``host`` given to the template's ``set_wrapper_*`` setter, or ``fallback``.

    The setter's ``host`` is the user's default host: steps that name their own target still win.
    """
    proxy_user = locust_wrapper_proxy.user_dict.get(proxy_key)
    return getattr(proxy_user, "host", None) or fallback


def with_connection_defaults(proxy_key: str, step: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the ``connection`` dict given to the setter under ``step``; keys in the step win.

    Returns ``step`` itself when no ``connection`` dict was given.
    """
    proxy_user = locust_wrapper_proxy.user_dict.get(proxy_key)
    connection = getattr(proxy_user, "connection", None)
    if not isinstance(connection, dict) or not connection:
        return step
    return {**connection, **step}


def payload_bytes(value: Any) -> bytes:
    """Encode a step's payload for sending.

    Text is UTF-8, bytes pass through, ``None`` is empty, dicts and lists become JSON, and any
    other value is sent as its text form. ``bytes(value)`` is not used: ``bytes(5)`` is five zero
    bytes, and ``bytes({...})`` raises.
    """
    if value is None:
        return b""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value).encode("utf-8")
    return str(value).encode("utf-8")


def coerce_response_length(value: Any) -> int:
    """Best-effort length for an arbitrary response payload."""
    if value is None:
        return 0
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    try:
        return len(value)
    except TypeError:
        return 1
