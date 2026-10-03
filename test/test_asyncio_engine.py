"""The asyncio engine against a local HTTP server.

The server and native client run in fresh interpreters because other tests select Locust,
whose gevent patching changes this process's socket and thread scheduling. No external network.
"""
import json
import socket
import subprocess  # nosec B404 - the test server is a child process
import sys
import tempfile
import time
import urllib.request

import pytest

pytest.importorskip("httpx")

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
    process = subprocess.Popen(  # nosec B603  # nosemgrep - fixed argument list, no shell
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
    # The suite also selects Locust. Exercise actual native I/O in an unpatched
    # interpreter, just like bench and the isolated desktop worker.
    source = """
import asyncio, faulthandler, json, sys
faulthandler.dump_traceback_later(8, repeat=True)
from je_load_density.engine.asyncio_engine import run_async_load
from je_load_density.utils.test_record.test_record_class import test_record_instance
options = json.loads(sys.argv[1])
result = asyncio.run(run_async_load(**options))
print(json.dumps({'result': result, 'success': test_record_instance.test_record_list,
                  'failure': test_record_instance.error_record_list}))
"""
    options = {"tasks": tasks, "users": 2, "duration_seconds": 1.0, **kwargs}
    arguments = [sys.executable, "-c", source, json.dumps(options)]
    # Locust patches subprocess communication in this parent; regular files avoid
    # gevent pipe-reader joins while keeping the same native child and timeout.
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors,
    ):
        # Security audit: Fixed interpreter/-c program; task options are JSON in sys.argv[1], not interpolated Python or
        # shell.
        # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
        child = subprocess.Popen(arguments, stdout=output, stderr=errors, text=True)
        try:
            deadline = time.monotonic() + 20
            while child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            if child.poll() is None:
                output.seek(0)
                errors.seek(0)
                # Security audit: Constructing TimeoutExpired only describes a timed-out process; it does not execute
                # arguments.
                # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
                raise subprocess.TimeoutExpired(arguments, 20, output.read(), errors.read())
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
        output.seek(0)
        errors.seek(0)
        stdout, stderr = output.read(), errors.read()
    assert child.returncode == 0, stdout + stderr
    measured = json.loads(stdout.splitlines()[-1])
    test_record_instance.test_record_list[:] = measured["success"]
    test_record_instance.error_record_list[:] = measured["failure"]
    return measured["result"]


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
    # Reserve a random port without listening, avoiding host-specific discard services/firewalls.
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{unused.getsockname()[1]}/nothing"
        _run([{"method": "get", "request_url": url, "timeout": 0.2}], users=1, duration_seconds=2.0)
    assert test_record_instance.error_record_list
    assert test_record_instance.error_record_list[0]["status_code"] == "0"


def test_max_in_flight_still_completes(base_url):
    summary = _run([{"method": "get", "request_url": f"{base_url}/ok"}], max_in_flight=1)
    assert summary["requests"] > 0
