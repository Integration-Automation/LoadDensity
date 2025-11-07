from je_load_density import start_test, generate_json_report

def test_http_user_test():
    start_test(
        {
            "user": "http_user",
        },
        10, 1, 10,
        **{
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }
    )
    generate_json_report()
