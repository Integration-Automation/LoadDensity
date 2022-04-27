from je_load_density import create_loading_test_user
from je_load_density import start_test

# create a dict include {request_method, request_url, assert_result_dict}
test_dict = {
    "request_method": "get",
    "request_url": "http://httpbin.org/get",
    "assert_result_dict": {"status_code": 200}
}
"""
start test use test_dict and use param
user_count: total use count will spawn
test_time: total test time
web_ui_dict: host: web ui host, port: web ui port
"""
start_test(
    create_loading_test_user(test_dict),
    user_count=50, test_time=10, spawn_rate=10,
    web_ui_dict={"host": "127.0.0.1", "port": 8089},
)
