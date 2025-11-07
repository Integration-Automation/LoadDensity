from je_load_density import callback_executor

print(
    callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=print,
        callback_param_method="args",
        callback_function_param={"": "test"},
        **{
            "user_detail_dict": {
                "user": "fast_http_user",
            },
            "user_count": 50,
            "spawn_rate": 10,
            "test_time": 5,
            **{
                "tasks": {
                    "get": {"request_url": "http://httpbin.org/get"},
                    "post": {"request_url": "http://httpbin.org/post"}
                }
            }
        }
    )
)
