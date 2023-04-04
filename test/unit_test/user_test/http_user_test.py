from je_load_density import start_test, generate_html_report

start_test(
    {
        "user": "http_user",
    },
    50, 10, 5,
    **{
        "tasks": {
            "get": {"request_url": "http://httpbin.org/get"},
            "post": {"request_url": "http://httpbin.org/post"}
        }
    }
)
generate_html_report()
