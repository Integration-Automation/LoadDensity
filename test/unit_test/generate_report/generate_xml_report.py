from je_load_density import generate_xml_report, start_test

def test_generate_xml_report():
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
    generate_xml_report()
