template_keyword_1: list = [
    ["LD_start_test", {
        "user_detail_dict": {
            "user": "fast_http_user"
        },
        "user_count": 50, "spawn_rate": 10, "test_time": 5,
        **{
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }
    }]
]

template_keyword_2: list = [
    ["LD_start_test", {
        "user_detail_dict": {
            "user": "http_user"
        },
        "user_count": 50, "spawn_rate": 10, "test_time": 5,
        **{
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }
    }]
]
