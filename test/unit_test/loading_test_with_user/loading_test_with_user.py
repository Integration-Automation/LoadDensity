from je_load_density import start_test

start_test(
    {
        "request_method": "get",
        "request_url": "http://httpbin.org/get"
    },
    50, 10, 20
)
