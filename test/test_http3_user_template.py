"""
The HTTP/3 template against a real aioquic server on 127.0.0.1 with a throwaway certificate.

The server (``h3_recording_server.py``) runs in its own process, logs every request, and answers
with the status named in the ``x-status`` request header (default 200) and a body of
``h3:<method>:<request body>``.
"""

import asyncio
import datetime
import ipaddress
import json
import socket
import subprocess  # nosec B404 - starts the test server with a fixed interpreter and script
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("aioquic")

from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402

from je_load_density.utils.parameterization import parameter_resolver  # noqa: E402
from je_load_density.wrapper.user_template.http3_user_template import Http3UserWrapper  # noqa: E402

SERVER_SCRIPT = Path(__file__).with_name("h3_recording_server.py")


def write_certificate(directory):
    """Self-signed certificate for 127.0.0.1; returns ``(cert_path, key_path)``."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .sign(key, hashes.SHA256())
    )
    cert_path = directory / "cert.pem"
    key_path = directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ))
    return cert_path, key_path


@pytest.fixture(autouse=True)
def isolated_resolver(monkeypatch):
    monkeypatch.setattr(parameter_resolver, "_variables", {})
    monkeypatch.setattr(parameter_resolver, "_csv_sources", {})


@pytest.fixture
def h3_server(tmp_path):
    cert_path, key_path = write_certificate(tmp_path)
    log_path = tmp_path / "requests.jsonl"
    log_path.touch()
    process = subprocess.Popen(  # nosemgrep  # nosec B603 - fixed interpreter and script
        [sys.executable, str(SERVER_SCRIPT), str(cert_path), str(key_path), str(log_path)],
        stdout=subprocess.PIPE, text=True,
    )
    try:
        port = int(process.stdout.readline())
        yield SimpleNamespace(
            url=f"https://127.0.0.1:{port}",
            ca_file=str(cert_path),
            requests=lambda: [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()],
        )
    finally:
        process.kill()
        process.wait(10)
        process.stdout.close()


def run_step(step):
    calls = []
    env = SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(fire=lambda **kw: calls.append(kw))))
    Http3UserWrapper(env)._do_step(step)
    assert len(calls) == 1  # nosec B101
    return calls[0]


def test_get_reads_the_response(h3_server):
    event = run_step({
        "method": "get", "request_url": f"{h3_server.url}/items?page=2", "ca_file": h3_server.ca_file,
        "headers": {"X-Trace": 7}, "timeout": 5,
    })

    assert event["exception"] is None  # nosec B101
    assert event["request_type"] == "HTTP/3"  # nosec B101
    assert event["response_length"] == len(b"h3:GET:")  # nosec B101
    request = h3_server.requests()[0]
    assert request["headers"][":path"] == "/items?page=2"  # nosec B101
    assert request["headers"]["x-trace"] == "7"  # nosec B101
    assert request["body"] == ""  # nosec B101


def test_post_sends_the_json_body_and_accepts_the_expected_status(h3_server):
    event = run_step({
        "method": "post", "request_url": f"{h3_server.url}/items", "ca_file": h3_server.ca_file,
        "json": {"a": 1}, "headers": {"X-Status": 201}, "expect_status": 201, "timeout": 5,
    })

    sent = json.dumps({"a": 1}).encode("utf-8")
    assert event["exception"] is None  # nosec B101
    assert event["response_length"] == len(b"h3:POST:" + sent)  # nosec B101
    assert h3_server.requests()[0]["body"] == sent.hex()  # nosec B101


def test_unexpected_status_fails_the_step(h3_server):
    event = run_step({
        "method": "get", "request_url": h3_server.url, "ca_file": h3_server.ca_file,
        "headers": {"X-Status": 503}, "expect_status": 200, "timeout": 5,
    })

    assert isinstance(event["exception"], AssertionError)  # nosec B101
    assert "expected 200, got 503" in str(event["exception"])  # nosec B101


def test_untrusted_certificate_fails_the_step(h3_server):
    event = run_step({"method": "get", "request_url": h3_server.url, "timeout": 5})

    assert event["exception"] is not None  # nosec B101
    assert h3_server.requests() == []  # nosec B101


def test_silent_endpoint_times_out():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as silent:
        silent.bind(("127.0.0.1", 0))
        port = silent.getsockname()[1]
        event = run_step({"method": "get", "request_url": f"https://127.0.0.1:{port}/", "timeout": 1})

    assert isinstance(event["exception"], (TimeoutError, asyncio.TimeoutError))  # nosec B101


def test_put_sends_a_raw_string_body_as_utf8(h3_server):
    event = run_step({
        "method": "put", "request_url": f"{h3_server.url}/items/1", "ca_file": h3_server.ca_file,
        "body": "héllo", "timeout": 5,
    })

    assert event["exception"] is None  # nosec B101
    assert h3_server.requests()[0]["body"] == "héllo".encode("utf-8").hex()  # nosec B101
