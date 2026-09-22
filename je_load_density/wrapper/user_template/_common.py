"""
Shared helpers for protocol user templates.

Centralises the Locust ``request`` event firing pattern so every new
template (SMTP, IMAP, FTP, AMQP, NATS, etc.) avoids duplicating the same
event-dispatch boilerplate.
"""

import json
import time
from typing import Any, Optional


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
