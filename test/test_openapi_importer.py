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
