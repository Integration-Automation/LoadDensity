from je_load_density.utils.recording.k6_importer import (
    k6_script_to_action_json,
    k6_script_to_tasks,
)


def test_k6_imports_simple_get():
    tasks = k6_script_to_tasks('http.get("https://api/health");')
    assert tasks == [{"method": "get", "request_url": "https://api/health"}]


def test_k6_imports_post_with_json_body():
    tasks = k6_script_to_tasks(
        'http.post("https://api/login", { "email": "u@x", "password": "s" });'
    )
    assert tasks[0]["method"] == "post"
    assert tasks[0]["json"] == {"email": "u@x", "password": "s"}


def test_k6_normalises_del_to_delete():
    tasks = k6_script_to_tasks('http.del("https://api/users/1");')
    assert tasks[0]["method"] == "delete"


def test_k6_extracts_status_assertion_from_check():
    source = """
    let res = http.get("https://api/x");
    check(res, { "is 200": (r) => r.status === 200 });
    """
    tasks = k6_script_to_tasks(source)
    assert tasks[0]["assertions"] == [{"type": "status_code", "value": 200}]


def test_k6_request_form_uses_first_arg_as_method():
    source = 'http.request("PUT", "https://api/x", "body");'
    tasks = k6_script_to_tasks(source)
    assert tasks[0]["method"] == "put"
    assert tasks[0]["request_url"] == "https://api/x"
    assert tasks[0]["data"] == "body"


def test_k6_action_json_wraps_correctly():
    action = k6_script_to_action_json('http.get("https://api/x");',
                                       user_count=15)
    inner = action["load_density"][0][1]
    assert inner["user_count"] == 15
    assert inner["tasks"]["tasks"][0]["request_url"] == "https://api/x"


def test_k6_handles_multiple_calls():
    source = """
    http.get("https://api/a");
    http.post("https://api/b", "payload");
    http.get("https://api/c");
    """
    tasks = k6_script_to_tasks(source)
    assert [t["request_url"] for t in tasks] == [
        "https://api/a", "https://api/b", "https://api/c",
    ]
