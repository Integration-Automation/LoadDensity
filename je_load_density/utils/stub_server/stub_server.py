"""
Service virtualization stub server (stdlib only).

Lets a load test run end-to-end without a real backend. The author
provides a list of rules; the first matching rule wins. Each rule::

    {"method": "GET", "path_regex": r"^/users/\\d+$",
     "status": 200, "headers": {"X-K": "v"},
     "json": {"id": 1}, "delay_ms": 0}
"""

import json as json_module
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

from je_load_density.utils.logging.loggin_instance import load_density_logger


_state: Dict[str, Any] = {
    "server": None,
    "thread": None,
    "rules": [],
}
_lock = threading.Lock()


def _match_rule(rules: List[Dict[str, Any]], method: str, path: str) -> Optional[Dict[str, Any]]:
    for rule in rules:
        if rule.get("method", "GET").upper() != method.upper():
            continue
        pattern = rule.get("path_regex") or rule.get("path") or ".*"
        if rule.get("path_regex") is None and rule.get("path") is not None:
            if rule["path"] != path:
                continue
        else:
            if not re.search(pattern, path):
                continue
        return rule
    return None


def _build_response(rule: Dict[str, Any]) -> Tuple[int, Dict[str, str], bytes]:
    status = int(rule.get("status", 200))
    headers = {str(k): str(v) for k, v in (rule.get("headers") or {}).items()}
    if "json" in rule:
        headers.setdefault("Content-Type", "application/json")
        body = json_module.dumps(rule["json"]).encode("utf-8")
    elif "body" in rule:
        body_value = rule["body"]
        body = body_value.encode("utf-8") if isinstance(body_value, str) else bytes(body_value)
    else:
        body = b""
    return status, headers, body


class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):  # noqa: D401
        return

    def _serve(self, method: str) -> None:
        rule = _match_rule(_state["rules"], method, self.path)
        if rule is None:
            self.send_response(404)
            self.end_headers()
            return
        delay_ms = int(rule.get("delay_ms", 0))
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        status, headers, body = _build_response(rule)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        self._serve("GET")

    def do_POST(self):  # noqa: N802
        self._serve("POST")

    def do_PUT(self):  # noqa: N802
        self._serve("PUT")

    def do_DELETE(self):  # noqa: N802
        self._serve("DELETE")

    def do_PATCH(self):  # noqa: N802
        self._serve("PATCH")


def start_stub_server(
    rules: List[Dict[str, Any]],
    host: str = "127.0.0.1",
    port: int = 0,
) -> Dict[str, Any]:
    """Start the stub server in a daemon thread. Returns ``{host, port}``."""
    with _lock:
        if _state["server"] is not None:
            return {"host": host, "port": _state["server"].server_address[1]}
        _state["rules"] = list(rules or [])
        server = ThreadingHTTPServer((host, port), _StubHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _state["server"] = server
        _state["thread"] = thread
        actual_port = server.server_address[1]
        load_density_logger.info(f"stub server started on {host}:{actual_port}")
        return {"host": host, "port": actual_port}


def stop_stub_server() -> None:
    """Stop the stub server if running."""
    with _lock:
        server = _state.get("server")
        if server is None:
            return
        try:
            server.shutdown()
            server.server_close()
        finally:
            _state["server"] = None
            _state["thread"] = None
            _state["rules"] = []
