from je_load_density.utils.recording.curl_importer import curl_to_task


def test_curl_simple_get():
    task = curl_to_task("curl https://api.example.com/health")
    assert task["method"] == "get"
    assert task["request_url"] == "https://api.example.com/health"


def test_curl_post_with_json_body_promotes_method_and_parses_json():
    cmd = """curl -X POST https://api/login \\
        -H 'Content-Type: application/json' \\
        -d '{"email":"u@x","password":"s"}'"""
    task = curl_to_task(cmd)
    assert task["method"] == "post"
    assert task["headers"]["Content-Type"] == "application/json"
    assert task["json"] == {"email": "u@x", "password": "s"}  # NOSONAR test fixture, not a credential


def test_curl_post_with_form_body():
    task = curl_to_task("curl -X POST https://api/x -d 'a=1&b=2'")
    assert task["data"] == "a=1&b=2"
    assert "json" not in task


def test_curl_basic_auth():
    task = curl_to_task("curl -u admin:rotate-me https://api/x")
    assert task["auth"] == {"type": "basic", "username": "admin", "password": "rotate-me"}  # NOSONAR test fixture


def test_curl_multiple_data_flags_join_with_amp():
    task = curl_to_task("curl -X POST https://api/x --data 'a=1' --data 'b=2'")
    assert task["data"] == "a=1&b=2"


def test_curl_insecure_and_location():
    task = curl_to_task("curl -k -L https://api/x")
    assert task["verify"] is False
    assert task["allow_redirects"] is True


def test_curl_method_defaults_to_post_when_data_present():
    task = curl_to_task("curl -d 'a=1' https://api/x")
    assert task["method"] == "post"
