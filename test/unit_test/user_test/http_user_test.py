from je_load_density import start_test

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
