"""Local smoke target in a fresh process, outside either runner's monkey patches."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = json.dumps({"ok": self.path != "/fail"}).encode("utf-8")
        self.send_response(500 if self.path == "/fail" else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if self.path != "/shutdown":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()
        Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        Path(sys.argv[1]).write_text(json.dumps({"port": server.server_port}), encoding="utf-8")
        server.serve_forever()
