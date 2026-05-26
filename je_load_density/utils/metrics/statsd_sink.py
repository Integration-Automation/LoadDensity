"""
Datadog DogStatsD UDP sink.

Listens to Locust request events and emits StatsD packets in the
Datadog dialect:

* ``loaddensity.requests:1|c|#method:get,name:/x,outcome:success``
* ``loaddensity.request.latency:42|ms|#method:get,name:/x``
* ``loaddensity.response.size:1024|h|#method:get,name:/x``

Pure UDP socket; no ``datadog`` SDK required.
"""

import socket
import threading
from typing import Any, Callable, List, Optional


_DEFAULT_PREFIX = "loaddensity"


class _StatsdEmitter:
    def __init__(self, host: str, port: int, prefix: str) -> None:
        self.host = host
        self.port = int(port)
        self.prefix = prefix.rstrip(".")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._lock = threading.Lock()

    def emit(self, packet: str) -> None:
        with self._lock:
            try:
                self._socket.sendto(packet.encode("utf-8"),
                                    (self.host, self.port))
            except OSError:
                return

    def close(self) -> None:
        try:
            self._socket.close()
        except OSError:
            pass


def _sanitize_tag_value(value: Any) -> str:
    text = str(value or "").replace("|", "_").replace(",", "_")
    return text.replace(":", "_").replace("#", "_")


def format_packets(
    prefix: str,
    method: str,
    name: str,
    response_time_ms: Optional[float],
    response_length: Optional[int],
    outcome: str,
) -> List[str]:
    tags = (f"method:{_sanitize_tag_value(method)},"
            f"name:{_sanitize_tag_value(name)},"
            f"outcome:{outcome}")
    packets = [f"{prefix}.requests:1|c|#{tags}"]
    if response_time_ms is not None:
        packets.append(f"{prefix}.request.latency:{int(response_time_ms)}|ms|#{tags}")
    if response_length is not None:
        packets.append(f"{prefix}.response.size:{int(response_length)}|h|#{tags}")
    return packets


_EMITTER: Optional[_StatsdEmitter] = None
_LISTENER: Optional[Callable] = None


def start_statsd_sink(host: str = "127.0.0.1", port: int = 8125,
                      prefix: str = _DEFAULT_PREFIX) -> _StatsdEmitter:
    """
    Subscribe to Locust request events and emit DogStatsD packets over
    UDP. Idempotent — calling twice rebinds.
    """
    global _EMITTER, _LISTENER
    stop_statsd_sink()
    emitter = _StatsdEmitter(host=host, port=port, prefix=prefix)

    def _listener(**kwargs):
        method = kwargs.get("request_type") or kwargs.get("method") or "REQ"
        name = kwargs.get("name") or kwargs.get("url") or "unknown"
        latency = kwargs.get("response_time")
        length = kwargs.get("response_length")
        outcome = "failure" if kwargs.get("exception") is not None else "success"
        for packet in format_packets(emitter.prefix, method, name,
                                       latency, length, outcome):
            emitter.emit(packet)

    try:
        from locust import events
        events.request.add_listener(_listener)
    except ImportError:  # pragma: no cover
        pass

    _EMITTER = emitter
    _LISTENER = _listener
    return emitter


def stop_statsd_sink() -> None:
    global _EMITTER, _LISTENER
    if _LISTENER is not None:
        try:
            from locust import events
            handlers = list(getattr(events.request, "_handlers", []))
            if _LISTENER in handlers:
                handlers.remove(_LISTENER)
                events.request._handlers = handlers
        except (ImportError, AttributeError):  # pragma: no cover
            pass
    if _EMITTER is not None:
        _EMITTER.close()
    _EMITTER = None
    _LISTENER = None
