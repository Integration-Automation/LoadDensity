from je_load_density import executor

def test_execute():
    test_list = [
        [
            "LD_start_test", {"user_detail_dict": {
                    "user": "fast_http_user"
                }, "user_count": 50, "spawn_rate": 10, "test_time": 5,
                "tasks": {
                    "get": {"request_url": "http://httpbin.org/get"},
                    "post": {"request_url": "http://httpbin.org/post"}
                }
            }
        ]
    ]
    executor.execute_action(test_list)
