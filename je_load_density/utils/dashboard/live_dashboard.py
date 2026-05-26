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
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional


_HTML = """<!doctype html>
<html><head><meta charset=utf-8><title>LoadDensity Live</title>
<style>
body{font-family:system-ui,sans-serif;margin:1.5rem;color:#222}
h1{font-weight:600;margin:0 0 .5rem 0}
section{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1rem 0}
.card{background:#f5f6fa;padding:1rem;border-radius:8px}
.card .v{font-size:2rem;font-weight:700}
.card .l{color:#666;font-size:.85rem;text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;margin-top:1rem;font-size:.9rem}
th,td{padding:.4rem .5rem;text-align:left;border-bottom:1px solid #eee}
</style></head>
<body>
<h1>LoadDensity Live</h1>
<section>
  <div class=card><div class=l>Total</div><div class=v id=total>0</div></div>
  <div class=card><div class=l>RPS</div><div class=v id=rps>0</div></div>
  <div class=card><div class=l>Avg ms</div><div class=v id=avg>0</div></div>
  <div class=card><div class=l>P95 ms</div><div class=v id=p95>0</div></div>
</section>
<table><thead><tr><th>Name</th><th>Count</th><th>Mean</th><th>P95</th></tr></thead>
<tbody id=tbody></tbody></table>
<script>
const es = new EventSource('/events');
es.onmessage = (event) => {
  const data = JSON.parse(event.data);
  document.getElementById('total').textContent = data.totals.requests;
  document.getElementById('rps').textContent = data.rps.toFixed(1);
  document.getElementById('avg').textContent = data.avg_ms.toFixed(0);
  document.getElementById('p95').textContent = data.latency_overall.p95_ms.toFixed(0);
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  for (const [name, stats] of Object.entries(data.per_name)) {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${name}</td><td>${stats.count}</td>` +
                    `<td>${stats.mean_ms.toFixed(0)}</td>` +
                    `<td>${stats.p95_ms.toFixed(0)}</td>`;
    tbody.appendChild(row);
  }
};
</script>
</body></html>
"""


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

    records: List[Dict[str, Any]] = list(test_record_instance.test_record_list)
    cutoff = time.time() - window_seconds
    recent = [r for r in records if r.get("ts") is None or float(r["ts"]) >= cutoff]
    latencies = [float(r.get("response_time_ms") or 0) for r in recent
                 if r.get("response_time_ms") is not None]
    rps = (len(recent) / window_seconds) if window_seconds > 0 else 0.0
    avg_ms = (sum(latencies) / len(latencies)) if latencies else 0.0

    return {
        "totals": summary["totals"],
        "latency_overall": summary["latency_overall"],
        "per_name": summary["per_name"],
        "rps": rps,
        "avg_ms": avg_ms,
        "ts": time.time(),
    }


class LiveDashboardServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 refresh_seconds: float = 1.0,
                 window_seconds: float = 10.0) -> None:
        self.host = host
        self.port = port
        self.refresh_seconds = refresh_seconds
        self.window_seconds = window_seconds
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        handler = _build_handler(self.refresh_seconds, self.window_seconds)
        self._httpd = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                         daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None


def _build_handler(refresh_seconds: float, window_seconds: float):

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):  # silence stdlib chatter
            return

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
                payload = json.dumps(snapshot_metrics(window_seconds)).encode("utf-8")
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
                while True:
                    payload = json.dumps(snapshot_metrics(window_seconds))
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(refresh_seconds)
            except (BrokenPipeError, ConnectionResetError):
                return

    return _Handler


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
