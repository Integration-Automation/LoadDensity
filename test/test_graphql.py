from je_load_density.utils.graphql.graphql_task import (
    extract_field,
    graphql_to_http_task,
)


def test_graphql_to_http_task_default():
    task = graphql_to_http_task("https://api/graphql", "{ me { id } }")
    assert task["method"] == "post"
    assert task["request_url"] == "https://api/graphql"
    assert task["json"]["query"] == "{ me { id } }"
    assert task["headers"]["Content-Type"] == "application/json"
    assert task["name"] == "GraphQL query"


def test_graphql_to_http_task_passes_variables_and_op_name():
    task = graphql_to_http_task(
        "https://api/graphql",
        "query GetUser($id: ID!) { user(id: $id) { name } }",
        variables={"id": "42"},
        operation_name="GetUser",
        headers={"Authorization": "Bearer x"},
    )
    assert task["json"]["variables"] == {"id": "42"}
    assert task["json"]["operationName"] == "GetUser"
    assert task["headers"]["Authorization"] == "Bearer x"
    assert task["name"] == "GraphQL GetUser"


def test_graphql_to_http_task_passes_assertions_and_extract():
    task = graphql_to_http_task(
        "https://api/graphql", "{ x }",
        assertions=[{"type": "status_code", "value": 200}],
        extract=[{"var": "x", "from": "json_path", "path": "data.x"}],
    )
    assert task["assertions"][0]["type"] == "status_code"
    assert task["extract"][0]["var"] == "x"


def test_extract_field_dotted_path():
    payload = {"data": {"user": {"id": "42", "tags": ["a", "b"]}}}
    assert extract_field(payload, "data.user.id") == "42"
    assert extract_field(payload, "data.user.tags.1") == "b"


def test_extract_field_missing_returns_none():
    assert extract_field({"data": {}}, "data.missing.name") is None
    assert extract_field({"data": {"x": "hi"}}, "data.x.y") is None
