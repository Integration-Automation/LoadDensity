from je_load_density import start_test

start_test(
    {
        "user": "multi_action_user",
    },
    50, 10, 5,
    **{
        "get": {"request_url": "http://httpbin.org/get"},
        "post": {"request_url": "http://httpbin.org/post"}
    }
)
