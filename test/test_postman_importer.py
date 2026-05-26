from je_load_density.utils.recording.postman_importer import (
    postman_to_action_json,
    postman_to_tasks,
)


COLLECTION = {
    "info": {"name": "demo", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "item": [
        {
            "name": "Health",
            "request": {
                "method": "GET",
                "header": [{"key": "X-Trace", "value": "1"}],
                "url": "https://api.example.com/health",
            },
        },
        {
            "name": "Folder",
            "item": [
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "url": {"raw": "https://api.example.com/login"},
                        "body": {"mode": "raw", "raw": '{"email":"u@x"}'},
                    },
                },
                {
                    "name": "Search",
                    "request": {
                        "method": "POST",
                        "url": "https://api.example.com/search",
                        "body": {
                            "mode": "urlencoded",
                            "urlencoded": [{"key": "q", "value": "hello"}],
                        },
                    },
                },
            ],
        },
    ],
}


def test_postman_to_tasks_walks_folders():
    tasks = postman_to_tasks(COLLECTION)
    names = [t["name"] for t in tasks]
    assert names == ["Health", "Login", "Search"]


def test_postman_get_carries_headers():
    tasks = postman_to_tasks(COLLECTION)
    health = tasks[0]
    assert health["method"] == "get"
    assert health["headers"] == {"X-Trace": "1"}


def test_postman_raw_json_body_parsed():
    tasks = postman_to_tasks(COLLECTION)
    login = tasks[1]
    assert login["method"] == "post"
    assert login["json"] == {"email": "u@x"}


def test_postman_urlencoded_body_becomes_dict():
    tasks = postman_to_tasks(COLLECTION)
    search = tasks[2]
    assert search["data"] == {"q": "hello"}


def test_postman_to_action_json_wraps_in_ld_start_test():
    action = postman_to_action_json(COLLECTION, user="http_user", user_count=5)
    inner = action["load_density"][0]
    assert inner[0] == "LD_start_test"
    assert inner[1]["user_detail_dict"] == {"user": "http_user"}
    assert inner[1]["user_count"] == 5
    assert inner[1]["tasks"]["mode"] == "sequence"
