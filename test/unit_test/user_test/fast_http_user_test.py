from je_load_density import start_test, generate_json_report

start_test(
    {
        "user": "fast_http_user",
    },
    1000, 100, 30,
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
