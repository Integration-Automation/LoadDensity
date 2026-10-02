"""
Live progress dashboard.

A stdlib-only HTTP + SSE server that streams running stats from
``test_record_instance`` so anyone with a browser can watch RPS,
average latency, p95, and failure count in real time.

Endpoints:

* ``GET /``         — static single-page HTML
* ``GET /events``   — Server-Sent Events; one JSON snapshot per
                       refresh interval
* ``GET /snapshot`` — one-shot JSON for polling clients
"""

import json
import threading
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import chain
from typing import Any, Dict, Optional

from je_load_density.utils.dashboard.dashboard_html import HTML
from je_load_density.utils.test_record.window_statistics import (
    finite_number,
    latency_mean,
    latency_windows,
    sample_time,
)

_HTML = HTML


def snapshot_metrics(window_seconds: float = 10.0) -> Dict[str, Any]:
    """
    Build a snapshot suitable for the dashboard. ``rps`` is the rolling
    request count over ``window_seconds`` from the in-memory record
    list.
    """
    from je_load_density.utils.generate_report.generate_summary_report import (
        build_summary,
    )
    from je_load_density.utils.test_record.test_record_class import (
        test_record_instance,
    )

    try:
        summary = build_summary()
    except Exception:
        summary = {"totals": {"requests": 0, "successes": 0, "failures": 0,
                              "failure_rate": 0.0},
                   "latency_overall": {"p50_ms": 0, "p90_ms": 0, "p95_ms": 0,
                                       "p99_ms": 0, "max_ms": 0, "count": 0},
                   "per_name": {}}

    duration = finite_number(window_seconds)
    if duration is None or duration <= 0:
        raise ValueError("window_seconds: expected a finite positive number")
    now = time.time()
    records = chain(test_record_instance.test_record_list, test_record_instance.error_record_list)
    windows = latency_windows(records, start=int(now) - 120, end=now, max_buckets=120)
    recent = [record for record in chain(test_record_instance.test_record_list, test_record_instance.error_record_list)
              if (timestamp := sample_time(record)) is not None and now - duration <= timestamp <= now]
    latencies = [latency for record in recent
                 if (latency := finite_number(record.get("response_time_ms"))) is not None and latency >= 0]
    rps = len(recent) / duration
    avg_ms = latency_mean(latencies)

    return {
        "totals": summary["totals"],
        "latency_overall": summary["latency_overall"],
        "per_name": summary["per_name"],
        "rps": rps,
        "avg_ms": avg_ms,
        "ts": now,
        "latency_windows": windows,
    }


class LiveDashboardServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 refresh_seconds: float = 1.0,
                 window_seconds: float = 10.0) -> None:
        self.host = host
        self.port = port
        self.refresh_seconds = refresh_seconds
        self.window_seconds = window_seconds
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()

    def start(self) -> None:
        if self._httpd is not None:
            raise RuntimeError("dashboard is already running")
        for name in ("refresh_seconds", "window_seconds"):
            value = finite_number(getattr(self, name))
            if value is None or value <= 0:
                raise ValueError(f"{name}: expected a finite positive number")
        self._stopping.clear()
        handler = _build_handler(self.refresh_seconds, self.window_seconds, self._stopping)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                         daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None


def _build_handler(refresh_seconds: float, window_seconds: float, stopping: threading.Event):
    return partial(_DashboardHandler, refresh_seconds=refresh_seconds, window_seconds=window_seconds, stopping=stopping)


class _DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, refresh_seconds, window_seconds, stopping):
        self.refresh_seconds = refresh_seconds
        self.window_seconds = window_seconds
        self.stopping = stopping
        super().__init__(*args)

    # pylint: disable=redefined-builtin
    def log_message(self, format, *args):  # noqa: A002 — match stdlib signature
        # Silence stdlib request-log chatter; the dashboard already
        # surfaces stats through SSE.
        del format, args

    def _write(self, status: int, body: bytes, content_type: str,
               extra_headers: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler protocol)
        if self.path == "/" or self.path == "/index.html":
            self._write(200, _HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/snapshot":
            payload = json.dumps(snapshot_metrics(self.window_seconds)).encode("utf-8")
            self._write(200, payload, "application/json")
            return
        if self.path == "/events":
            self._serve_sse()
            return
        self._write(404, b"not found", "text/plain")

    def _serve_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while not self.stopping.is_set():
                payload = json.dumps(snapshot_metrics(self.window_seconds))
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.stopping.wait(self.refresh_seconds)
        except (BrokenPipeError, ConnectionResetError):
            return



_SERVER: Optional[LiveDashboardServer] = None


def start_dashboard(host: str = "127.0.0.1", port: int = 8765,
                    refresh_seconds: float = 1.0,
                    window_seconds: float = 10.0) -> LiveDashboardServer:
    global _SERVER
    stop_dashboard()
    _SERVER = LiveDashboardServer(host=host, port=port,
                                   refresh_seconds=refresh_seconds,
                                   window_seconds=window_seconds)
    _SERVER.start()
    return _SERVER


def stop_dashboard() -> None:
    global _SERVER
    if _SERVER is not None:
        _SERVER.stop()
        _SERVER = None
