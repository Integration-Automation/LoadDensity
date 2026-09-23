"""
LoadDensity MCP server.

Exposes load test execution, report generation, HAR import, and project
init as MCP tools so Claude can drive LoadDensity.

The protocol is spoken directly -- JSON-RPC 2.0, one message per line on
stdin/stdout -- instead of through the ``mcp`` SDK. Importing LoadDensity
imports locust, which gevent-monkey-patches ``threading``; the SDK's stdio
transport reads stdin from a worker thread, that thread then never runs,
and the SDK server never answered a single request. Reading stdin on the
main thread has no such dependency.

Run with:

    python -m je_load_density.mcp_server
"""

import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from je_load_density.utils.action_generator.generate import (
    generate_from_curls,
    generate_from_openapi,
)
from je_load_density.utils.executor.action_executor import execute_action, executor
from je_load_density.utils.generate_report.generate_csv_report import generate_csv_report
from je_load_density.utils.generate_report.generate_html_report import generate_html_report
from je_load_density.utils.generate_report.generate_json_report import generate_json_report
from je_load_density.utils.generate_report.generate_junit_report import generate_junit_report
from je_load_density.utils.generate_report.generate_summary_report import (
    build_summary,
    generate_summary_report,
)
from je_load_density.utils.generate_report.generate_xml_report import generate_xml_report
from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.utils.project.create_project_structure import create_project_dir
from je_load_density.utils.recording.har_importer import har_to_action_json, load_har
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_run_records,
    list_runs,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.start_wrapper.start_test import start_test


_JSONRPC_VERSION = "2.0"
# Newest first; an ``initialize`` asking for another version gets the newest.
_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602


class _RequestError(Exception):
    """A request the server answers with a JSON-RPC error object."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": _JSONRPC_VERSION, "id": msg_id, "error": {"code": code, "message": message}}


def _text_content(value: Any) -> List[Dict[str, str]]:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return [{"type": "text", "text": text}]


def _package_version() -> str:
    try:
        return metadata.version("je_load_density")
    except metadata.PackageNotFoundError:
        return "0"


def _tool_run_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    return start_test(**payload)


# Tools take file paths from the client, which here is a language model and may be steered by the
# content it reads; every path is confined to this root (the working directory unless set).
MCP_ROOT_ENV = "JE_LOAD_DENSITY_MCP_ROOT"


def _confined(value: Any) -> str:
    """Resolve ``value`` against the MCP root and refuse anything outside it.

    Relative paths are taken from the root; ``..`` and absolute paths are allowed only while the
    resolved path stays inside it.
    """
    root = Path(os.environ.get(MCP_ROOT_ENV) or os.getcwd()).resolve()
    candidate = Path(str(value))
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path {value!r} is outside the MCP root {root}; set {MCP_ROOT_ENV} to widen it")
    return str(resolved)


def _tool_run_action_string(payload: Dict[str, Any]) -> Dict[str, Any]:
    actions = payload.get("actions")
    if isinstance(actions, str):
        actions = json.loads(actions)
    return execute_action(actions)


def _tool_create_project(payload: Dict[str, Any]) -> Dict[str, str]:
    path = _confined(payload["path"])
    create_project_dir(path)
    return {"path": path, "status": "created"}


def _tool_list_executor_commands(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"commands": sorted(name for name in executor.event_dict.keys() if name.startswith("LD_"))}


def _tool_import_har(payload: Dict[str, Any]) -> Dict[str, Any]:
    har = load_har(_confined(payload["file_path"]))
    return har_to_action_json(
        har,
        user=payload.get("user", "fast_http_user"),
        user_count=int(payload.get("user_count", 10)),
        spawn_rate=int(payload.get("spawn_rate", 5)),
        test_time=int(payload.get("test_time", 60)),
        include=payload.get("include"),
        exclude=payload.get("exclude"),
    )


def _tool_generate_reports(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    base = _confined(payload.get("base_name", "loaddensity"))
    formats = payload.get("formats") or ["html", "json", "xml", "csv", "junit", "summary"]
    result: Dict[str, Optional[str]] = {}
    if "html" in formats:
        result["html"] = generate_html_report(base)
    if "json" in formats:
        result["json"] = generate_json_report(base)
    if "xml" in formats:
        result["xml"] = generate_xml_report(base)
    if "csv" in formats:
        result["csv"] = generate_csv_report(base)
    if "junit" in formats:
        result["junit"] = generate_junit_report(f"{base}-junit")
    if "summary" in formats:
        result["summary"] = generate_summary_report(f"{base}-summary")
    return result


def _tool_summary(_: Dict[str, Any]) -> Dict[str, Any]:
    return build_summary()


def _tool_persist_records(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_id = persist_records(
        _confined(payload["database_path"]),
        label=payload.get("label"),
        metadata=payload.get("metadata"),
    )
    return {"run_id": run_id}


def _tool_list_runs(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"runs": list_runs(_confined(payload["database_path"]), limit=int(payload.get("limit", 20)))}


def _tool_fetch_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"records": list(fetch_run_records(_confined(payload["database_path"]), int(payload["run_id"])))}


def _tool_clear_records(_: Dict[str, Any]) -> Dict[str, str]:
    test_record_instance.clear_records()
    return {"status": "cleared"}


def _tool_generate_from_openapi(payload: Dict[str, Any]) -> Dict[str, Any]:
    return generate_from_openapi(
        openapi_path=_confined(payload["openapi_path"]),
        user=payload.get("user", "fast_http_user"),
        user_count=int(payload.get("user_count", 20)),
        spawn_rate=int(payload.get("spawn_rate", 5)),
        test_time=int(payload.get("test_time", 60)),
        variables=payload.get("variables"),
        base_url=payload.get("base_url"),
    )


def _tool_generate_from_curls(payload: Dict[str, Any]) -> Dict[str, Any]:
    curls = payload.get("curls") or []
    return generate_from_curls(
        curls=list(curls),
        user=payload.get("user", "fast_http_user"),
        user_count=int(payload.get("user_count", 20)),
        spawn_rate=int(payload.get("spawn_rate", 5)),
        test_time=int(payload.get("test_time", 60)),
        variables=payload.get("variables"),
    )


_TOOLS: Dict[str, Dict[str, Any]] = {
    "load_density.run_test": {
        "description": "Run a Locust-backed load test via start_test.",
        "handler": _tool_run_test,
        "input_schema": {
            "type": "object",
            "properties": {
                "user_detail_dict": {"type": "object"},
                "user_count": {"type": "integer", "default": 50},
                "spawn_rate": {"type": "integer", "default": 10},
                "test_time": {"type": "integer", "default": 60},
                "tasks": {},
                "variables": {"type": "object"},
                "csv_sources": {"type": "array"},
                "runner_mode": {"type": "string", "default": "local"},
                "web_ui_dict": {"type": "object"},
            },
            "required": ["user_detail_dict"],
        },
    },
    "load_density.run_action_json": {
        "description": "Execute an action JSON document (string or list).",
        "handler": _tool_run_action_string,
        "input_schema": {
            "type": "object",
            "properties": {"actions": {}},
            "required": ["actions"],
        },
    },
    "load_density.create_project": {
        "description": "Create a LoadDensity project skeleton at PATH.",
        "handler": _tool_create_project,
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "load_density.list_executor_commands": {
        "description": "List all LD_* executor commands.",
        "handler": _tool_list_executor_commands,
        "input_schema": {"type": "object", "properties": {}},
    },
    "load_density.import_har": {
        "description": "Convert a HAR file into a runnable action JSON.",
        "handler": _tool_import_har,
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "user": {"type": "string"},
                "user_count": {"type": "integer"},
                "spawn_rate": {"type": "integer"},
                "test_time": {"type": "integer"},
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["file_path"],
        },
    },
    "load_density.generate_reports": {
        "description": "Render reports (html/json/xml/csv/junit/summary).",
        "handler": _tool_generate_reports,
        "input_schema": {
            "type": "object",
            "properties": {
                "base_name": {"type": "string"},
                "formats": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "load_density.summary": {
        "description": "Return aggregated stats (totals, per-name percentiles).",
        "handler": _tool_summary,
        "input_schema": {"type": "object", "properties": {}},
    },
    "load_density.persist_records": {
        "description": "Persist current records into a SQLite database.",
        "handler": _tool_persist_records,
        "input_schema": {
            "type": "object",
            "properties": {
                "database_path": {"type": "string"},
                "label": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["database_path"],
        },
    },
    "load_density.list_runs": {
        "description": "List recent persisted runs.",
        "handler": _tool_list_runs,
        "input_schema": {
            "type": "object",
            "properties": {
                "database_path": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["database_path"],
        },
    },
    "load_density.fetch_run": {
        "description": "Fetch records belonging to a saved run.",
        "handler": _tool_fetch_run,
        "input_schema": {
            "type": "object",
            "properties": {
                "database_path": {"type": "string"},
                "run_id": {"type": "integer"},
            },
            "required": ["database_path", "run_id"],
        },
    },
    "load_density.clear_records": {
        "description": "Clear in-memory test records before a new run.",
        "handler": _tool_clear_records,
        "input_schema": {"type": "object", "properties": {}},
    },
    "load_density.generate_from_openapi": {
        "description": "Build a runnable action JSON from an OpenAPI spec.",
        "handler": _tool_generate_from_openapi,
        "input_schema": {
            "type": "object",
            "properties": {
                "openapi_path": {"type": "string"},
                "user": {"type": "string"},
                "user_count": {"type": "integer"},
                "spawn_rate": {"type": "integer"},
                "test_time": {"type": "integer"},
                "variables": {"type": "object"},
                "base_url": {"type": "string"},
            },
            "required": ["openapi_path"],
        },
    },
    "load_density.generate_from_curls": {
        "description": "Build a runnable action JSON from a list of cURL commands.",
        "handler": _tool_generate_from_curls,
        "input_schema": {
            "type": "object",
            "properties": {
                "curls": {"type": "array", "items": {"type": "string"}},
                "user": {"type": "string"},
                "user_count": {"type": "integer"},
                "spawn_rate": {"type": "integer"},
                "test_time": {"type": "integer"},
                "variables": {"type": "object"},
            },
            "required": ["curls"],
        },
    },
}


class LoadDensityMCPServer:
    """
    MCP server for ``_TOOLS``: ``initialize``, ``ping``, ``tools/list`` and
    ``tools/call`` over newline-delimited JSON-RPC 2.0.

    Notifications (``notifications/initialized``, ``notifications/cancelled``)
    get no reply. A tool that raises is reported as an ``isError`` result, as
    MCP asks; an unknown tool or method is a JSON-RPC error.
    """

    def __init__(self, tools: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self.tools = _TOOLS if tools is None else tools
        self._methods = {
            "initialize": self._initialize,
            "ping": lambda _params: {},
            "tools/list": self._list_tools,
            "tools/call": self._call_tool,
        }

    def handle_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """Answer one decoded message; ``None`` when it needs no reply."""
        if not isinstance(message, dict) or message.get("jsonrpc") != _JSONRPC_VERSION:
            return _error(None, _INVALID_REQUEST, "expected a JSON-RPC 2.0 object")
        if "method" not in message or "id" not in message:
            return None  # a notification, or a response to a request never sent
        msg_id = message["id"]
        handler = self._methods.get(message["method"])
        if handler is None:
            return _error(msg_id, _METHOD_NOT_FOUND, f"unknown method: {message['method']}")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(msg_id, _INVALID_PARAMS, "params must be an object")
        try:
            result = handler(params)
        except _RequestError as error:
            return _error(msg_id, error.code, str(error))
        return {"jsonrpc": _JSONRPC_VERSION, "id": msg_id, "result": result}

    def serve(self, reader: TextIO, writer: TextIO) -> None:
        """Answer every line of ``reader`` on ``writer`` until end of input."""
        for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                response = _error(None, _PARSE_ERROR, f"invalid JSON: {error}")
            else:
                response = self.handle_message(message)
            if response is not None:
                writer.write(json.dumps(response, default=str) + "\n")
                writer.flush()

    @staticmethod
    def _initialize(params: Dict[str, Any]) -> Dict[str, Any]:
        requested = params.get("protocolVersion")
        return {
            "protocolVersion": requested if requested in _PROTOCOL_VERSIONS else _PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "loaddensity", "version": _package_version()},
        }

    def _list_tools(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {"tools": [
            {"name": name, "description": meta["description"], "inputSchema": meta["input_schema"]}
            for name, meta in self.tools.items()
        ]}

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        tool = self.tools.get(name) if isinstance(name, str) else None
        if tool is None:
            raise _RequestError(_INVALID_PARAMS, f"unknown tool: {name}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise _RequestError(_INVALID_PARAMS, "arguments must be an object")
        try:
            result = tool["handler"](arguments)
        # reason: a tool may raise anything; MCP reports that as an isError result, not a protocol error
        except Exception as error:  # noqa: BLE001  # pylint: disable=broad-except
            load_density_logger.error(f"mcp tool {name} failed: {error!r}")
            return {"content": _text_content(f"{type(error).__name__}: {error}"), "isError": True}
        return {"content": _text_content(result), "isError": False}


def build_server() -> LoadDensityMCPServer:
    """
    Build the MCP server with the LoadDensity tool surface.
    """
    return LoadDensityMCPServer()


def run_stdio() -> None:
    """
    Run the MCP server over stdio (the standard transport for Claude).

    Side effect: for the rest of the process, anything else written to
    stdout -- ``print`` actions, locust's console output, child processes --
    goes to stderr, so only protocol messages reach the client. Both
    directions are UTF-8 whatever the console code page.
    """
    protocol_out = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", newline="\n")
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    reader = open(sys.stdin.fileno(), encoding="utf-8", closefd=False)  # noqa: SIM115 - wraps the process stdin
    with protocol_out, reader:
        build_server().serve(reader, protocol_out)
