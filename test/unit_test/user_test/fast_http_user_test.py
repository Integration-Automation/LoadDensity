from je_load_density import start_test, generate_json_report

def test_fast_http_user_test():
    start_test(
        {
            "user": "fast_http_user",
        },
        10, 1, 10,
        web_ui_dict=
        {
            "host": "127.0.0.1",
            "port": 8089
        },
        ** {
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }
    )
    generate_json_report()
