"""
Minimal Language Server Protocol implementation for LoadDensity action
JSON files.

Implements just enough of LSP 3.17 to make VS Code, JetBrains LSP
plugin, and Neovim happy:

* ``initialize`` / ``initialized`` / ``shutdown`` / ``exit``
* ``textDocument/didOpen`` / ``didChange`` (text sync) →
  ``textDocument/publishDiagnostics`` (runs the action linter)
* ``textDocument/completion`` → completion items for every registered
  ``LD_*`` command.

The server only depends on the Python standard library; no ``pygls`` or
``lsprotocol`` runtime requirement.
"""

import json
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from je_load_density.utils.executor.action_executor import executor
from je_load_density.utils.linter.action_linter import lint_action

_SEVERITY = {"error": 1, "warning": 2, "info": 3, "hint": 4}


def _read_message(reader) -> Optional[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    while True:
        line = reader.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n", b""):
            break
        if b":" in line:
            name, _, value = line.partition(b":")
            headers[name.decode("ascii").strip().lower()] = value.decode("ascii").strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    payload = reader.read(length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def _write_message(writer, message: Dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    writer.write(header + body)
    writer.flush()


class ActionLspServer:
    def __init__(self) -> None:
        self._documents: Dict[str, str] = {}
        self._known_commands = sorted(
            name for name in executor.event_dict if name.startswith("LD_")
        )
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            "initialize": self._on_initialize,
            "initialized": self._on_initialized,
            "textDocument/didOpen": self._on_did_open,
            "textDocument/didChange": self._on_did_change,
            "textDocument/completion": self._on_completion,
            "shutdown": self._on_shutdown,
            "exit": self._on_exit,
        }
        self._shutdown = False
        self._diagnostics_writer = None

    # ------------------------------------------------------------------ wire
    def attach(self, reader, writer) -> None:
        self._diagnostics_writer = writer
        while not self._shutdown:
            message = _read_message(reader)
            if message is None:
                return
            self._dispatch(reader, writer, message)

    def _dispatch(self, reader, writer, message: Dict[str, Any]) -> None:
        method = message.get("method")
        handler = self._handlers.get(method)
        if handler is None:
            self._send_response(writer, message.get("id"),
                                error={"code": -32601, "message": f"unknown method: {method}"})
            return
        try:
            result = handler(message.get("params") or {})
        except Exception as error:  # pragma: no cover (LSP must never crash)
            self._send_response(writer, message.get("id"),
                                error={"code": -32603, "message": repr(error)})
            return
        if "id" in message:
            self._send_response(writer, message["id"], result=result)

    @staticmethod
    def _send_response(writer, msg_id, result=None, error=None) -> None:
        if msg_id is None:
            return
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id}
        if error is not None:
            payload["error"] = error
        else:
            payload["result"] = result
        _write_message(writer, payload)

    # ------------------------------------------------------------------ rpc
    def _on_initialize(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "capabilities": {
                "textDocumentSync": 1,  # full document sync
                "completionProvider": {"triggerCharacters": ["\"", "_"]},
            },
            "serverInfo": {"name": "loaddensity-action-lsp", "version": "1.0"},
        }

    def _on_initialized(self, _params: Dict[str, Any]) -> None:
        return None

    def _on_did_open(self, params: Dict[str, Any]) -> None:
        document = params.get("textDocument") or {}
        uri = document.get("uri", "")
        text = document.get("text", "")
        self._documents[uri] = text
        self._publish_diagnostics(uri, text)

    def _on_did_change(self, params: Dict[str, Any]) -> None:
        uri = (params.get("textDocument") or {}).get("uri", "")
        changes = params.get("contentChanges") or []
        if changes:
            text = changes[-1].get("text", "")
            self._documents[uri] = text
            self._publish_diagnostics(uri, text)

    def _on_completion(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        items = [{"label": name, "kind": 14, "detail": "LoadDensity LD_* command"}
                 for name in self._known_commands]
        return {"isIncomplete": False, "items": items}

    def _on_shutdown(self, _params: Dict[str, Any]) -> None:
        self._shutdown = True
        return None

    def _on_exit(self, _params: Dict[str, Any]) -> None:
        self._shutdown = True
        return None

    # -------------------------------------------------------- diagnostics
    def _publish_diagnostics(self, uri: str, text: str) -> None:
        if self._diagnostics_writer is None:
            return
        diagnostics = self._compute_diagnostics(text)
        _write_message(self._diagnostics_writer, {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": uri, "diagnostics": diagnostics},
        })

    def _compute_diagnostics(self, text: str) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(text) if text.strip() else []
        except json.JSONDecodeError as error:
            return [_diagnostic_at(error.lineno - 1, error.colno - 1,
                                    f"invalid JSON: {error.msg}",
                                    severity="error")]
        findings = lint_action(payload, known_commands=set(self._known_commands))
        return [_diagnostic_at(0, 0, f"[{f['rule']}] {f['message']}",
                                severity=f["severity"])
                for f in findings]


def _diagnostic_at(line: int, character: int, message: str,
                    severity: str = "warning") -> Dict[str, Any]:
    line = max(0, line)
    character = max(0, character)
    return {
        "range": {"start": {"line": line, "character": character},
                  "end": {"line": line, "character": character + 1}},
        "severity": _SEVERITY.get(severity, 2),
        "source": "loaddensity",
        "message": message,
    }


def serve_stdio() -> None:
    server = ActionLspServer()
    server.attach(sys.stdin.buffer, sys.stdout.buffer)


# Exported for tests
def compute_diagnostics(text: str) -> List[Dict[str, Any]]:
    return ActionLspServer()._compute_diagnostics(text)


def completion_items() -> Tuple[List[str], List[Dict[str, Any]]]:
    server = ActionLspServer()
    result = server._on_completion({})
    return server._known_commands, result["items"]
