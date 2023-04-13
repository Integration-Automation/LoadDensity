from je_load_density import generate_json_report, start_test
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
