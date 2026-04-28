import threading
from typing import Any, Dict, Optional

from locust import events

from je_load_density.utils.logging.loggin_instance import load_density_logger

_state: Dict[str, Any] = {
    "started": False,
    "listener": None,
    "metrics": None,
}
_lock = threading.Lock()


def _build_metrics():
    from prometheus_client import Counter, Histogram

    return {
        "requests": Counter(
            "loaddensity_requests_total",
            "Total Locust requests",
            ["request_type", "name", "outcome"],
        ),
        "latency": Histogram(
            "loaddensity_request_latency_ms",
            "Locust request latency in milliseconds",
            ["request_type", "name"],
            buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
        ),
        "response_size": Histogram(
            "loaddensity_response_bytes",
            "Locust response size in bytes",
            ["request_type", "name"],
            buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576),
        ),
    }


def start_prometheus_exporter(port: int = 9646, addr: str = "127.0.0.1") -> Optional[int]:
    """
    啟動 Prometheus 指標伺服器並掛上 Locust request 事件監聽。
    Start the Prometheus exporter HTTP server and attach a request listener.

    Defaults to binding on loopback. Pass ``addr="0.0.0.0"`` explicitly
    to expose the exporter to the network when running in a container
    or remote node.

    Returns the port the exporter is listening on, or None if the optional
    dependency is not installed.
    """
    with _lock:
        if _state["started"]:
            return port
        try:
            from prometheus_client import start_http_server
        except ImportError:
            load_density_logger.warning("prometheus_client not installed; exporter disabled")
            return None

        metrics = _build_metrics()
        start_http_server(port, addr=addr)

        def _listener(request_type, name, response_time, response_length, exception=None, **_kwargs):
            outcome = "failure" if exception is not None else "success"
            metrics["requests"].labels(request_type=str(request_type), name=str(name), outcome=outcome).inc()
            metrics["latency"].labels(request_type=str(request_type), name=str(name)).observe(float(response_time or 0))
            metrics["response_size"].labels(request_type=str(request_type), name=str(name)).observe(float(response_length or 0))

        events.request.add_listener(_listener)
        _state["started"] = True
        _state["listener"] = _listener
        _state["metrics"] = metrics
        load_density_logger.info(f"Prometheus exporter started on {addr}:{port}")
        return port


def stop_prometheus_exporter() -> None:
    """
    從 Locust 事件移除監聽器（注意 prometheus_client 的 server 無法輕易停止）。
    Detach the listener; prometheus_client's server keeps running.
    """
    with _lock:
        if not _state["started"]:
            return
        try:
            events.request.remove_listener(_state["listener"])
        except Exception as error:
            load_density_logger.debug(f"prometheus listener detach failed: {error!r}")
        _state["started"] = False
        _state["listener"] = None
