"""
OpenTelemetry tracing exporter — one span per Locust request.

Complements the existing metrics exporter; emits OTLP gRPC spans so
LoadDensity runs show up as distributed traces in Tempo/Jaeger.
"""

import threading
import time
from typing import Any, Dict, Optional

from locust import events

from je_load_density.utils.logging.loggin_instance import load_density_logger

_state: Dict[str, Any] = {
    "started": False,
    "listener": None,
    "provider": None,
    "tracer": None,
}
_lock = threading.Lock()


def _build_tracer_provider(endpoint: Optional[str], service_name: str):
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name})
    exporter_kwargs: Dict[str, Any] = {}
    if endpoint:
        exporter_kwargs["endpoint"] = endpoint
    exporter = OTLPSpanExporter(**exporter_kwargs)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider, trace.get_tracer("loaddensity")


def start_opentelemetry_tracing_exporter(
    endpoint: Optional[str] = None,
    service_name: str = "loaddensity",
) -> bool:
    """Start a per-request OTLP tracing exporter."""
    with _lock:
        if _state["started"]:
            return True
        try:
            provider, tracer = _build_tracer_provider(endpoint, service_name)
        except ImportError:
            load_density_logger.warning(
                "opentelemetry SDK not installed; tracing exporter disabled"
            )
            return False
        except Exception as error:
            load_density_logger.warning(f"OTel tracing init failed: {error!r}")
            return False

        def _listener(
            request_type, name, response_time, response_length, exception=None, **_kwargs,
        ):
            end = time.time_ns()
            start = end - int(float(response_time or 0) * 1_000_000)
            with tracer.start_as_current_span(
                f"{request_type} {name}",
                start_time=start,
                attributes={
                    "request.type": str(request_type),
                    "request.name": str(name),
                    "response.length": int(response_length or 0),
                    "outcome": "failure" if exception is not None else "success",
                },
            ) as span:
                if exception is not None:
                    span.record_exception(exception)
                span.end(end_time=end)

        events.request.add_listener(_listener)
        _state["started"] = True
        _state["listener"] = _listener
        _state["provider"] = provider
        _state["tracer"] = tracer
        load_density_logger.info("OpenTelemetry tracing exporter started")
        return True


def stop_opentelemetry_tracing_exporter() -> None:
    with _lock:
        if not _state["started"]:
            return
        try:
            events.request.remove_listener(_state["listener"])
        except Exception as error:
            load_density_logger.debug(f"otel tracing listener detach failed: {error!r}")
        provider = _state.get("provider")
        if provider is not None:
            try:
                provider.shutdown()
            except Exception as error:
                load_density_logger.debug(f"otel tracing shutdown failed: {error!r}")
        _state["started"] = False
        _state["listener"] = None
        _state["provider"] = None
        _state["tracer"] = None
