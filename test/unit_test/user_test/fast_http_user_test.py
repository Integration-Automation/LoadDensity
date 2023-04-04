from je_load_density import start_test, generate_json_report

start_test(
    {
        "user": "fast_http_user",
    },
    50, 10, 5,
    **{
        "tasks": {
            "get": {"request_url": "http://httpbin.org/get"},
            "post": {"request_url": "http://httpbin.org/post"}
        }
    }
)
generate_json_report()
