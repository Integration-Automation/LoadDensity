"""The control server end to end: a child process runs it under gevent, a client runs an action and stops it."""
import json
import socket
import subprocess  # noqa: S404 - runs this interpreter with a fixed argument list
import sys
import time
from pathlib import Path

END = b"Return_Data_Over_JE\n"
_CHILD = (
    "import sys\n"
    "from je_load_density.utils.socket_server.load_density_socket_server import start_load_density_socket_server\n"
    "start_load_density_socket_server(host='127.0.0.1', port=int(sys.argv[1]))\n"
)
_STARTUP_SECONDS = 60


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _ask(port: int, payload: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=10) as client:
        client.sendall(payload)
        chunks = []
        chunk = client.recv(4096)
        while chunk:
            chunks.append(chunk)
            chunk = client.recv(4096)
    return b"".join(chunks)


def _wait_for(port: int) -> None:
    deadline = time.monotonic() + _STARTUP_SECONDS
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"server did not listen on {port}")


def _wait_for_exit(child: subprocess.Popen) -> int:
    # Polling, not communicate(): locust gevent-patches this test process, and the patched communicate()
    # can block on Windows pipes after the child has already exited.
    deadline = time.monotonic() + _STARTUP_SECONDS
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.2)
    return child.poll()


def test_child_process_serves_and_stops(tmp_path):
    port = _free_port()
    repository = Path(__file__).resolve().parents[1]
    output = tmp_path / "server.out"
    with output.open("w", encoding="utf-8") as sink:
        child = subprocess.Popen([sys.executable, "-c", _CHILD, str(port)], cwd=repository,  # noqa: S603
                                 stdout=sink, stderr=subprocess.STDOUT)
        try:
            _wait_for(port)
            assert _ask(port, json.dumps([["len", [[1, 2, 3]]]]).encode()) == b"3\n" + END
            assert _ask(port, b"quit_server") == b"Server shutting down\n"
            assert _wait_for_exit(child) == 0
        finally:
            if child.poll() is None:
                child.kill()
    text = output.read_text(encoding="utf-8", errors="replace")
    assert f"Server started on 127.0.0.1:{port}" in text
    assert "Server shutdown complete" in text
