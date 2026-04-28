import threading
from typing import Any, Dict, Optional

from locust import events

from je_load_density.utils.logging.loggin_instance import load_density_logger

_state: Dict[str, Any] = {
    "started": False,
    "listener": None,
    "instruments": None,
    "provider": None,
}
_lock = threading.Lock()


def _build_provider(endpoint: Optional[str], service_name: str, export_interval_ms: int):
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": service_name})
    exporter_kwargs: Dict[str, Any] = {}
    if endpoint:
        exporter_kwargs["endpoint"] = endpoint
    exporter = OTLPMetricExporter(**exporter_kwargs)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=export_interval_ms)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider, metrics.get_meter("loaddensity")


def _build_instruments(meter):
    return {
        "requests": meter.create_counter(
            "loaddensity.requests",
            unit="1",
            description="Locust request count",
        ),
        "latency": meter.create_histogram(
            "loaddensity.request.latency",
            unit="ms",
            description="Locust request latency",
        ),
        "size": meter.create_histogram(
            "loaddensity.response.size",
            unit="By",
            description="Locust response size",
        ),
    }


def start_opentelemetry_exporter(
    endpoint: Optional[str] = None,
    service_name: str = "loaddensity",
    export_interval_ms: int = 5000,
) -> bool:
    """
    啟動 OpenTelemetry OTLP 指標輸出。
    Start an OpenTelemetry OTLP metrics exporter and attach a Locust
    request listener.
    """
    with _lock:
        if _state["started"]:
            return True
        try:
            provider, meter = _build_provider(endpoint, service_name, export_interval_ms)
        except ImportError:
            load_density_logger.warning(
                "opentelemetry SDK not installed; OTel exporter disabled"
            )
            return False
        except Exception as error:
            load_density_logger.warning(f"OTel exporter init failed: {error!r}")
            return False

        instruments = _build_instruments(meter)

        def _listener(request_type, name, response_time, response_length, exception=None, **_kwargs):
            attributes = {
                "request_type": str(request_type),
                "name": str(name),
                "outcome": "failure" if exception is not None else "success",
            }
            instruments["requests"].add(1, attributes)
            instruments["latency"].record(float(response_time or 0), attributes)
            instruments["size"].record(int(response_length or 0), attributes)

        events.request.add_listener(_listener)
        _state["started"] = True
        _state["listener"] = _listener
        _state["instruments"] = instruments
        _state["provider"] = provider
        load_density_logger.info("OpenTelemetry exporter started")
        return True


def stop_opentelemetry_exporter() -> None:
    with _lock:
        if not _state["started"]:
            return
        try:
            events.request.remove_listener(_state["listener"])
        except Exception:
            pass
        provider = _state.get("provider")
        if provider is not None:
            try:
                provider.shutdown()
            except Exception:
                pass
        _state["started"] = False
        _state["listener"] = None
        _state["instruments"] = None
        _state["provider"] = None
