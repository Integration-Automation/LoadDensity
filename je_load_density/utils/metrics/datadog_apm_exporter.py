"""
Datadog APM exporter — one ddtrace span per Locust request.

Lazy-imports ``ddtrace``; gated by the ``datadog`` install extra.
"""

import threading
from typing import Any, Dict, Optional

from locust import events

from je_load_density.utils.logging.loggin_instance import load_density_logger

_state: Dict[str, Any] = {
    "started": False,
    "listener": None,
    "tracer": None,
}
_lock = threading.Lock()


def _import_ddtrace():
    try:
        from ddtrace import tracer  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "ddtrace is required for the Datadog APM exporter; "
            "install with: pip install ddtrace"
        ) from error
    return tracer


def start_datadog_apm_exporter(
    service: str = "loaddensity",
    env: Optional[str] = None,
    agent_url: Optional[str] = None,
) -> bool:
    """Start a per-request ddtrace span emitter."""
    with _lock:
        if _state["started"]:
            return True
        try:
            tracer = _import_ddtrace()
        except RuntimeError as error:
            load_density_logger.warning(str(error))
            return False
        if agent_url:
            try:
                tracer.configure(hostname=None, port=None, uds_path=None)
            except Exception as error:
                load_density_logger.debug(f"ddtrace configure failed: {error!r}")

        def _listener(
            request_type, name, response_time, response_length, exception=None, **_kwargs,
        ):
            span = tracer.trace(
                f"{request_type}.{name}",
                service=service,
                resource=str(name),
                span_type="http",
            )
            try:
                span.set_tag("request.type", str(request_type))
                span.set_tag("request.name", str(name))
                span.set_tag("response.length", int(response_length or 0))
                if env:
                    span.set_tag("env", env)
                if exception is not None:
                    span.set_tag("error.type", type(exception).__name__)
                    span.set_tag("error.msg", str(exception))
                    span.error = 1
                duration_ns = int(float(response_time or 0) * 1_000_000)
                span.finish(finish_time=(span.start_ns + duration_ns) / 1e9)
            except Exception as inner:  # nosec - non-fatal observability path
                load_density_logger.debug(f"ddtrace emit failed: {inner!r}")
                span.finish()

        events.request.add_listener(_listener)
        _state["started"] = True
        _state["listener"] = _listener
        _state["tracer"] = tracer
        load_density_logger.info("Datadog APM exporter started")
        return True


def stop_datadog_apm_exporter() -> None:
    with _lock:
        if not _state["started"]:
            return
        try:
            events.request.remove_listener(_state["listener"])
        except Exception as error:
            load_density_logger.debug(f"ddtrace listener detach failed: {error!r}")
        _state["started"] = False
        _state["listener"] = None
        _state["tracer"] = None
