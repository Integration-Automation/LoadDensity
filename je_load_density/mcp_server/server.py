"""
LoadDensity MCP server.

Exposes load test execution, report generation, HAR import, and project
init as MCP tools so Claude can drive LoadDensity. The mcp SDK is
imported lazily so the dependency stays optional.

Run with:

    python -m je_load_density.mcp_server
"""

import json
from typing import Any, Dict, List, Optional

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
from je_load_density.utils.project.create_project_structure import create_project_dir
from je_load_density.utils.recording.har_importer import har_to_action_json, load_har
from je_load_density.utils.test_record.sqlite_persistence import (
    fetch_run_records,
    list_runs,
    persist_records,
)
from je_load_density.utils.test_record.test_record_class import test_record_instance
from je_load_density.wrapper.start_wrapper.start_test import start_test


def _ensure_mcp():
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types as mcp_types
    except ImportError as error:
        raise RuntimeError(
            "mcp package is required. Install with: pip install mcp"
        ) from error
    return Server, stdio_server, mcp_types


def _wrap_text(value: Any, mcp_types) -> List[Any]:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return [mcp_types.TextContent(type="text", text=text)]


def _tool_run_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    return start_test(**payload)


def _tool_run_action_string(payload: Dict[str, Any]) -> Dict[str, Any]:
    actions = payload.get("actions")
    if isinstance(actions, str):
        actions = json.loads(actions)
    return execute_action(actions)


def _tool_create_project(payload: Dict[str, Any]) -> Dict[str, str]:
    create_project_dir(payload["path"])
    return {"path": payload["path"], "status": "created"}


def _tool_list_executor_commands(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"commands": sorted(name for name in executor.event_dict.keys() if name.startswith("LD_"))}


def _tool_import_har(payload: Dict[str, Any]) -> Dict[str, Any]:
    har = load_har(payload["file_path"])
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
    base = payload.get("base_name", "loaddensity")
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
        payload["database_path"],
        label=payload.get("label"),
        metadata=payload.get("metadata"),
    )
    return {"run_id": run_id}


def _tool_list_runs(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"runs": list_runs(payload["database_path"], limit=int(payload.get("limit", 20)))}


def _tool_fetch_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"records": list(fetch_run_records(payload["database_path"], int(payload["run_id"])))}


def _tool_clear_records(_: Dict[str, Any]) -> Dict[str, str]:
    test_record_instance.clear_records()
    return {"status": "cleared"}


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
}


def build_server():
    """
    Build the MCP Server instance with the LoadDensity tool surface.
    """
    server_cls, _, mcp_types = _ensure_mcp()
    server = server_cls("loaddensity")

    @server.list_tools()
    async def _list_tools():
        return [
            mcp_types.Tool(
                name=name,
                description=meta["description"],
                inputSchema=meta["input_schema"],
            )
            for name, meta in _TOOLS.items()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: Optional[Dict[str, Any]]):
        tool = _TOOLS.get(name)
        if tool is None:
            raise ValueError(f"unknown tool: {name}")
        result = tool["handler"](arguments or {})
        return _wrap_text(result, mcp_types)

    return server


def run_stdio() -> None:
    """
    Run the MCP server over stdio (the standard transport for Claude).
    """
    _, stdio_server, _ = _ensure_mcp()
    server = build_server()

    import asyncio

    async def _main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_main())
