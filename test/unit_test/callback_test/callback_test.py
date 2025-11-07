from je_load_density import callback_executor

def test_callback_executor_runs():
    result = callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=lambda x: x,  # 用 lambda 取代 print，方便驗證回傳值
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

    # 驗證 callback_executor 有回傳結果
    assert result is not None