import socket
import threading
import time
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from locust import events

from je_load_density.utils.logging.loggin_instance import load_density_logger

_state: Dict[str, Any] = {
    "started": False,
    "listener": None,
    "config": None,
}
_lock = threading.Lock()


def _escape_tag(value: str) -> str:
    return str(value).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def _escape_field_string(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _build_line(measurement: str, tags: Dict[str, str], fields: Dict[str, Any], timestamp_ns: int) -> str:
    tag_segment = ",".join(f"{_escape_tag(k)}={_escape_tag(v)}" for k, v in tags.items() if v is not None)
    field_segments = []
    for key, value in fields.items():
        if isinstance(value, bool):
            field_segments.append(f"{key}={'true' if value else 'false'}")
        elif isinstance(value, (int,)):
            field_segments.append(f"{key}={value}i")
        elif isinstance(value, float):
            field_segments.append(f"{key}={value}")
        else:
            field_segments.append(f'{key}="{_escape_field_string(value)}"')
    field_segment = ",".join(field_segments)
    head = f"{measurement},{tag_segment}" if tag_segment else measurement
    return f"{head} {field_segment} {timestamp_ns}"


def _send_udp(line: str, host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(line.encode("utf-8"), (host, port))
    finally:
        sock.close()


_ALLOWED_HTTP_SCHEMES = ("http://", "https://")


def _send_http(line: str, url: str, token: Optional[str], timeout: float) -> None:
    if not url.lower().startswith(_ALLOWED_HTTP_SCHEMES):
        raise ValueError("InfluxDB HTTP URL must use http:// or https://")
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib_request.Request(url, data=line.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:  # nosec B310 - scheme validated above
            response.read()
    except urllib_error.URLError as error:
        load_density_logger.warning(f"InfluxDB HTTP write failed: {error}")


def start_influxdb_sink(
    transport: str = "udp",
    host: str = "127.0.0.1",
    port: int = 8089,
    url: Optional[str] = None,
    token: Optional[str] = None,
    measurement: str = "loaddensity_request",
    timeout: float = 2.0,
) -> bool:
    """
    啟動 InfluxDB sink，將每個 request 寫入 line protocol。
    Start an InfluxDB sink that writes each request as a line-protocol
    point. transport=udp uses host:port; transport=http requires url.

    URL is caller-supplied so this defers to the operator's configured
    InfluxDB endpoint; not a hard-coded destination.
    """
    transport = transport.lower()
    if transport not in {"udp", "http"}:
        raise ValueError(f"unsupported transport: {transport}")
    if transport == "http":
        if not url:
            raise ValueError("url required when transport=http")
        if not url.lower().startswith(_ALLOWED_HTTP_SCHEMES):
            raise ValueError("InfluxDB HTTP URL must use http:// or https://")

    with _lock:
        if _state["started"]:
            return True

        config = {
            "transport": transport,
            "host": host,
            "port": port,
            "url": url,
            "token": token,
            "measurement": measurement,
            "timeout": timeout,
        }

        def _listener(request_type, name, response_time, response_length, exception=None, **_kwargs):
            tags = {"request_type": str(request_type), "name": str(name)}
            fields: Dict[str, Any] = {
                "latency_ms": float(response_time or 0),
                "response_bytes": int(response_length or 0),
                "success": exception is None,
            }
            if exception is not None:
                fields["error"] = repr(exception)[:512]
            line = _build_line(measurement, tags, fields, time.time_ns())
            try:
                if transport == "udp":
                    _send_udp(line, host, port)
                else:
                    _send_http(line, url, token, timeout)
            except Exception as error:
                load_density_logger.debug(f"InfluxDB write failed: {error}")

        events.request.add_listener(_listener)
        _state["started"] = True
        _state["listener"] = _listener
        _state["config"] = config
        load_density_logger.info(f"InfluxDB sink started transport={transport}")
        return True


def stop_influxdb_sink() -> None:
    with _lock:
        if not _state["started"]:
            return
        try:
            events.request.remove_listener(_state["listener"])
        except Exception as error:
            load_density_logger.debug(f"influxdb listener detach failed: {error!r}")
        _state["started"] = False
        _state["listener"] = None
        _state["config"] = None
