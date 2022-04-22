from je_load_density import create_loading_test_user
from je_load_density import start_test

test_dict = {
    "request_method": "get",
    "request_url": "http://httpbin.org/get",
    "assert_result_dict": {"status_code": 200}
}
start_test(
    create_loading_test_user(test_dict),
    user_count=50, test_time=180, spawn_rate=10,
    web_ui_dict={"host": "127.0.0.1", "port": 8089},
)
