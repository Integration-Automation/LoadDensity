"""Real tests for the chaos helpers (progress.md #1): the Toxiproxy client and the Chaos Mesh launcher.

Toxiproxy is replaced by a local HTTP server that records every call; kubectl by a stand-in for
``subprocess.run``. Nothing leaves the machine.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from je_load_density.utils.chaos import chaos_mesh, toxiproxy


class _Recorder(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *_args):
        return

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        type(self).calls.append((self.command, self.path, json.loads(body) if body else None))
        payload = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_DELETE = _handle


@pytest.fixture()
def toxiproxy_api():
    _Recorder.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", _Recorder.calls
    server.shutdown()
    server.server_close()


def test_proxy_and_toxic_calls_hit_the_documented_endpoints(toxiproxy_api):
    base, calls = toxiproxy_api
    toxiproxy.create_proxy("api", "127.0.0.1:26379", "redis:6379", base_url=base)
    toxiproxy.install_latency("api", 250, jitter_ms=20, base_url=base)
    toxiproxy.install_bandwidth("api", 64, base_url=base)
    toxiproxy.remove_toxic("api", "api-latency", base_url=base)
    toxiproxy.reset_all(base_url=base)
    toxiproxy.remove_proxies(["api"], base_url=base)
    assert toxiproxy.list_proxies(base_url=base) == {"ok": True}
    assert [(method, path) for method, path, _ in calls] == [
        ("POST", "/proxies"),
        ("POST", "/proxies/api/toxics"),
        ("POST", "/proxies/api/toxics"),
        ("DELETE", "/proxies/api/toxics/api-latency"),
        ("POST", "/reset"),
        ("DELETE", "/proxies/api"),
        ("GET", "/proxies"),
    ]
    assert calls[0][2] == {"name": "api", "listen": "127.0.0.1:26379", "upstream": "redis:6379", "enabled": True}
    assert calls[1][2] == {"name": "api-latency", "type": "latency", "stream": "downstream",
                           "attributes": {"latency": 250, "jitter": 20}}
    assert calls[2][2]["attributes"] == {"rate": 64}


def test_names_cannot_reach_another_endpoint(toxiproxy_api):
    base, calls = toxiproxy_api
    toxiproxy.remove_proxies(["a/../../reset"], base_url=base)
    assert calls[-1][:2] == ("DELETE", "/proxies/a%2F..%2F..%2Freset")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://host/x"])
def test_only_http_urls_are_accepted(url):
    with pytest.raises(ValueError, match="scheme"):
        toxiproxy.list_proxies(base_url=url)


def test_network_delay_manifest_shape():
    manifest = chaos_mesh.build_network_delay("slow-api", "shop", {"app": "api"}, latency="200ms", duration="1m")
    assert manifest["kind"] == "NetworkChaos"
    assert manifest["metadata"] == {"name": "slow-api", "namespace": "shop"}
    assert manifest["spec"]["delay"] == {"latency": "200ms"}
    assert manifest["spec"]["selector"] == {"labelSelectors": {"app": "api"}}
    assert manifest["spec"]["duration"] == "1m"


@pytest.fixture()
def fake_kubectl(monkeypatch):
    seen = []

    def fake_run(argv, **_kwargs):
        manifest_path = Path(argv[argv.index("-f") + 1])
        seen.append((argv, json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path))
        return SimpleNamespace(returncode=0, stdout=b"networkchaos/slow-api configured", stderr=b"")

    monkeypatch.setattr(chaos_mesh.shutil, "which", lambda _name: "kubectl")
    monkeypatch.setattr(chaos_mesh.subprocess, "run", fake_run)
    return seen


def test_apply_writes_the_manifest_and_cleans_up(fake_kubectl):
    manifest = chaos_mesh.build_network_delay("slow-api", "shop", {"app": "api"})
    output = chaos_mesh.apply_manifest(manifest, namespace="shop")
    argv, written, path = fake_kubectl[0]
    assert output == "networkchaos/slow-api configured"
    assert argv[:2] == ["kubectl", "apply"]
    assert argv[-2:] == ["-n", "shop"]
    assert written == manifest
    assert not path.exists()


def test_delete_ignores_missing_resources(fake_kubectl):
    chaos_mesh.delete_manifest({"kind": "NetworkChaos"})
    argv = fake_kubectl[0][0]
    assert argv[1] == "delete"
    assert "--ignore-not-found" in argv
    assert "-n" not in argv


def test_kubectl_failure_raises_with_its_stderr(monkeypatch):
    monkeypatch.setattr(chaos_mesh.shutil, "which", lambda _name: "kubectl")
    monkeypatch.setattr(chaos_mesh.subprocess, "run",
                        lambda *_a, **_k: SimpleNamespace(returncode=1, stdout=b"", stderr=b"no cluster"))
    with pytest.raises(RuntimeError, match="no cluster"):
        chaos_mesh.apply_manifest({"kind": "NetworkChaos"})


def test_missing_kubectl_is_reported(monkeypatch):
    monkeypatch.setattr(chaos_mesh.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="kubectl not found"):
        chaos_mesh.apply_manifest({"kind": "NetworkChaos"})
