"""The asyncio engine against a local HTTP server (progress.md #1).

The server runs in its own interpreter: importing LoadDensity imports locust, whose gevent
patching turns a server thread in this process into a greenlet that never gets scheduled while
asyncio holds the main thread -- an in-process stub would only ever time out. No external network.
"""
import asyncio
import subprocess  # nosec B404 - the test server is a child process
import sys
import time
import urllib.request

import pytest

pytest.importorskip("httpx")

from je_load_density.engine.asyncio_engine import run_async_load  # noqa: E402
from je_load_density.utils.test_record.test_record_class import test_record_instance  # noqa: E402

_SERVER = """
import http.server, sys
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_GET(self):
        status, body = (500, b"down") if self.path == "/boom" else (200, b'{"ok": true}')
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(server.server_address[1], flush=True)
server.serve_forever()
"""


@pytest.fixture(scope="module")
def base_url():
    process = subprocess.Popen(  # nosec B603  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
        [sys.executable, "-c", _SERVER], stdout=subprocess.PIPE, text=True)
    try:
        port = int(process.stdout.readline())
        url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{url}/ok", timeout=1).read()  # nosec B310 - loopback test server
                break
            except OSError:
                time.sleep(0.1)
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(autouse=True)
def _clean_records():
    test_record_instance.clear_records()
    yield
    test_record_instance.clear_records()


def _run(tasks, **kwargs):
    return asyncio.run(run_async_load(tasks=tasks, users=2, duration_seconds=1.0, **kwargs))


def test_successful_requests_are_recorded(base_url):
    summary = _run([{"method": "get", "request_url": f"{base_url}/ok"}])
    assert summary["requests"] > 0
    assert summary["failures"] == 0
    record = test_record_instance.test_record_list[0]
    assert record["status_code"] == "200"
    assert record["response_length"] == len(b'{"ok": true}')
    assert record["start_time"] > 0


def test_server_errors_count_as_failures_like_locust(base_url):
    summary = _run([{"method": "get", "request_url": f"{base_url}/boom"}])
    assert summary["requests"] == 0
    assert summary["failures"] > 0
    record = test_record_instance.error_record_list[0]
    assert record["status_code"] == "500"
    assert record["error"] == "HTTP 500"


def test_connection_failures_are_recorded_with_status_zero():
    # Port 9 (discard) on loopback refuses the connection.
    _run([{"method": "get", "request_url": "http://127.0.0.1:9/nothing", "timeout": 0.5}])
    assert test_record_instance.error_record_list
    assert test_record_instance.error_record_list[0]["status_code"] == "0"


def test_max_in_flight_still_completes(base_url):
    summary = _run([{"method": "get", "request_url": f"{base_url}/ok"}], max_in_flight=1)
    assert summary["requests"] > 0
