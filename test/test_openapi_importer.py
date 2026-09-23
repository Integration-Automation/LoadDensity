from je_load_density.utils.recording.openapi_importer import (
    openapi_to_action_json,
    openapi_to_tasks,
)


SPEC = {
    "openapi": "3.0.0",
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {
        "/health": {"get": {"operationId": "getHealth",
                            "responses": {"200": {"description": "ok"}}}},
        "/users/{id}": {
            "get": {"operationId": "getUser",
                    "responses": {"200": {"description": "ok"}}},
            "delete": {"operationId": "deleteUser",
                       "responses": {"204": {"description": "gone"}}},
        },
    },
}


def test_openapi_emits_one_task_per_method():
    tasks = openapi_to_tasks(SPEC)
    op_ids = [t["name"] for t in tasks]
    assert set(op_ids) == {"getHealth", "getUser", "deleteUser"}


def test_openapi_substitutes_path_params_with_var_placeholders():
    tasks = openapi_to_tasks(SPEC)
    user_get = next(t for t in tasks if t["name"] == "getUser")
    assert user_get["request_url"] == "https://api.example.com/v1/users/${var.id}"


def test_openapi_status_assertion_picks_first_2xx():
    tasks = openapi_to_tasks(SPEC)
    delete = next(t for t in tasks if t["name"] == "deleteUser")
    assert delete["assertions"] == [{"type": "status_code", "value": 204}]


def test_openapi_to_action_json_wraps_correctly():
    action = openapi_to_action_json(SPEC, user_count=20)
    inner = action["load_density"][0][1]
    assert inner["user_detail_dict"] == {"user": "fast_http_user"}
    assert inner["user_count"] == 20
    assert len(inner["tasks"]["tasks"]) == 3


def test_openapi_handles_missing_servers():
    spec_no_servers = {"openapi": "3.0.0",
                       "paths": {"/x": {"get": {"responses": {"200": {}}}}}}
    tasks = openapi_to_tasks(spec_no_servers)
    assert tasks[0]["request_url"] == "/x"


def _spec_file(tmp_path):
    import json

    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(SPEC), encoding="utf-8")
    return str(path)


def _urls(document):
    start = next(action[1] for action in document["load_density"] if action[0] == "LD_start_test")
    return [task["request_url"] for task in start["tasks"]]


def test_generate_from_openapi_uses_the_spec_server(tmp_path):
    from je_load_density.utils.action_generator.generate import generate_from_openapi

    urls = _urls(generate_from_openapi(_spec_file(tmp_path)))
    assert urls and all(url.startswith("https://api.example.com/v1/") for url in urls)


def test_generate_from_openapi_base_url_replaces_the_server(tmp_path):
    from je_load_density.utils.action_generator.generate import generate_from_openapi

    urls = _urls(generate_from_openapi(_spec_file(tmp_path), base_url="http://staging.test/"))
    assert urls and all(url.startswith("http://staging.test/") for url in urls)


def test_mcp_generate_from_openapi_tool_runs(tmp_path):
    from je_load_density.mcp_server import server

    document = server._tool_generate_from_openapi({"openapi_path": _spec_file(tmp_path), "base_url": "http://s.test"})
    assert all(url.startswith("http://s.test/") for url in _urls(document))
