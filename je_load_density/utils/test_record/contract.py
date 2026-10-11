"""Adapt existing LoadDensity records without changing legacy report consumers."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from je_action_core.request_context import RunContext
    from je_action_core.request_record import RequestRecord

_SENSITIVE_HEADERS = frozenset(("authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key"))
_HTTP_METHODS = frozenset(("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "CONNECT", "TRACE"))


def _number(record: Mapping[str, object], field: str, converter):
    value = record.get(field)
    if value is None:
        return None
    try:
        return converter(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{field}: invalid measurement") from error


def _fields(record: Mapping[str, object], outcome: str) -> dict[str, object]:
    method = str(record.get("Method") or "GET").upper()
    url = str(record.get("test_url") or "")
    start = _number(record, "start_time", float)
    elapsed = _number(record, "response_time_ms", float)
    status = _number(record, "status_code", int)
    failure = None if outcome == "passed" else {
        "kind": str(record.get("error_kind") or "request"),
        "message": str(record.get("error") or "request failed"),
    }
    protocol = record.get("protocol") or ("http" if method in _HTTP_METHODS else method.lower())
    return {"protocol": str(protocol), "request_method": method,
            "request_url": url, "name": str(record.get("name") or f"{method} {url}"),
            "status_code": status if status != 0 else None, "start_time": start,
            "end_time": start + elapsed / 1000.0 if start is not None and elapsed is not None else None,
            "response_time_ms": elapsed, "response_length": _number(record, "response_length", int),
            "outcome": outcome, "error": failure, "assertions": record.get("assertions") or [],
            "step_id": record.get("step_id"), "scenario_id": record.get("scenario_id")}


def _payload(record: Mapping[str, object]) -> dict[str, object]:
    fields: dict[str, object] = {}
    if "text" in record:
        fields["text"] = record["text"]
    headers = record.get("headers")
    if isinstance(headers, Mapping):
        fields["headers"] = {
            str(key): "[REDACTED]" if str(key).lower() in _SENSITIVE_HEADERS else str(value)
            for key, value in headers.items()
        }
    content = record.get("content")
    if isinstance(content, bytes):
        fields["content_base64"] = base64.b64encode(content).decode("ascii")
    return fields


def from_legacy_record(record: Mapping[str, object], context: RunContext, outcome: str,
                       capture_payload: bool = False) -> RequestRecord:
    """Import one legacy result into the selected run, preserving unknown measurements as null."""
    fields = _fields(record, outcome)
    if capture_payload:
        fields.update(_payload(record))
    return context.capture(fields)


def get_optional_run_context() -> RunContext | None:
    """Return a selected context, keeping legacy-only imports usable with earlier core releases."""
    try:
        from je_action_core.request_context import get_run_context
    except ModuleNotFoundError as error:
        if error.name != "je_action_core.request_context":
            raise
        return None
    return get_run_context()


def record_request(record: Mapping[str, object], outcome: str, capture_payload: bool = False) -> RequestRecord | None:
    """Capture only when a run scope is active; older core versions retain legacy-only behavior."""
    context = get_optional_run_context()
    if context is None:
        return None
    return from_legacy_record(record, context, outcome, capture_payload)
