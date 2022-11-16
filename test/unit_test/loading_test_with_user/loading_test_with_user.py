from je_load_density import loading_test_with_user

loading_test_with_user(
    {
        "request_method": "get",
        "request_url": "http://httpbin.org/get"
    },
    50, 10, 20
)
