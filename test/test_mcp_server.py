"""The MCP server speaks JSON-RPC 2.0 over stdio without the ``mcp`` SDK.

The SDK's stdio transport never answered once locust had gevent-patched
``threading`` (``docs/updates`` U-20260923-02), so the end-to-end test runs the
real entry point as a child process, where that patching happens.
"""
import json
import os
import subprocess  # nosec B404 - the server is exercised as a real child process
import sys
from pathlib import Path

import pytest

from je_load_density.mcp_server import build_server
from je_load_density.mcp_server.server import LoadDensityMCPServer

REPO_ROOT = Path(__file__).resolve().parents[1]


def _request(msg_id, method, params=None):
    message = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def _tools_by_name():
    return {tool["name"]: tool for tool in build_server().handle_message(_request(1, "tools/list"))["result"]["tools"]}


def test_initialize_echoes_a_supported_protocol_version():
    result = build_server().handle_message(_request(1, "initialize", {"protocolVersion": "2025-03-26"}))["result"]
    assert result["protocolVersion"] == "2025-03-26"
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    assert result["serverInfo"]["name"] == "loaddensity"


def test_initialize_offers_the_newest_version_for_an_unknown_one():
    result = build_server().handle_message(_request(1, "initialize", {"protocolVersion": "1999-01-01"}))["result"]
    assert result["protocolVersion"] == "2025-06-18"


def test_tools_list_matches_the_tool_table():
    tools = _tools_by_name()
    assert len(tools) == 13
    for tool in tools.values():
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_tools_call_returns_text_content():
    response = build_server().handle_message(
        _request(7, "tools/call", {"name": "load_density.list_executor_commands", "arguments": {}}))
    assert response["id"] == 7
    assert response["result"]["isError"] is False
    commands = json.loads(response["result"]["content"][0]["text"])["commands"]
    assert commands and all(name.startswith("LD_") for name in commands)


def test_a_failing_tool_is_an_error_result_not_a_protocol_error():
    def boom(_payload):
        raise ValueError("bad input")

    server = LoadDensityMCPServer({"t": {"description": "d", "handler": boom, "input_schema": {"type": "object"}}})
    result = server.handle_message(_request(1, "tools/call", {"name": "t"}))["result"]
    assert result["isError"] is True
    assert "ValueError: bad input" in result["content"][0]["text"]


def test_protocol_errors():
    server = build_server()
    assert server.handle_message(_request(1, "tools/call", {"name": "nope"}))["error"]["code"] == -32602
    assert server.handle_message(_request(2, "resources/list"))["error"]["code"] == -32601
    assert server.handle_message(_request(3, "tools/list", ["not", "an", "object"]))["error"]["code"] == -32602
    assert server.handle_message({"id": 4, "method": "ping"})["error"]["code"] == -32600


def test_notifications_and_ping():
    server = build_server()
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.handle_message(_request(1, "ping")) == {"jsonrpc": "2.0", "id": 1, "result": {}}


def test_stdio_round_trip_in_a_child_process(tmp_path):
    marker = "stray-print-must-not-reach-the-protocol"
    lines = [
        _request(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                   "clientInfo": {"name": "test", "version": "0"}}),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _request(2, "tools/list"),
        _request(3, "tools/call", {"name": "load_density.run_action_json",
                                   "arguments": {"actions": [["print", [marker]]]}}),
        _request(4, "tools/call", {"name": "load_density.create_project",
                                   "arguments": {"path": str(tmp_path / "項目")}}),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO_ROOT), env.get("PYTHONPATH")]))
    result = subprocess.run(  # nosec B603  # nosemgrep - fixed argument list, no shell
        [sys.executable, "-m", "je_load_density.mcp_server"],
        input="".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines).encode("utf-8"),
        cwd=tmp_path, env=env, capture_output=True, timeout=300, check=False,
    )
    stdout = result.stdout.decode("utf-8")
    responses = [json.loads(line) for line in stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2, 3, 4], stdout + result.stderr.decode("utf-8", "replace")
    assert responses[0]["result"]["serverInfo"]["name"] == "loaddensity"
    assert len(responses[1]["result"]["tools"]) == 13
    assert responses[2]["result"]["isError"] is False
    # Every stdout line parsed as JSON above; the printed line went to stderr instead.
    assert marker in result.stderr.decode("utf-8", "replace").splitlines()
    assert responses[3]["result"]["isError"] is False
    assert (tmp_path / "項目").is_dir()


def test_tool_paths_are_confined_to_the_root(tmp_path, monkeypatch):
    from je_load_density.mcp_server import server

    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv(server.MCP_ROOT_ENV, str(root))
    assert server._confined("runs.db") == str(root / "runs.db")
    assert server._confined(str(root / "sub" / "x.json")) == str(root / "sub" / "x.json")
    for outside in ("../escape.db", str(tmp_path / "other.db"), "sub/../../escape.db"):
        with pytest.raises(ValueError, match="outside the MCP root"):
            server._confined(outside)


def test_create_project_outside_the_root_is_refused(tmp_path, monkeypatch):
    from je_load_density.mcp_server import server

    monkeypatch.setenv(server.MCP_ROOT_ENV, str(tmp_path / "root"))
    (tmp_path / "root").mkdir()
    with pytest.raises(ValueError):
        server._tool_create_project({"path": str(tmp_path / "elsewhere")})
    assert not (tmp_path / "elsewhere").exists()
