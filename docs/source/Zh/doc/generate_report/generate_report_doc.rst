報告產生
----

Generate Report 可以生成以下格式的報告

* HTML
* JSON
* XML
* Generate Report 主要用來記錄與確認有哪些步驟執行，執行是否成功，
* 如果要使用 Generate Report 需要先設定紀錄為 True，使用 test_record_instance.init_record = True
* 下面的範例有搭配 keyword and executor 如果看不懂可以先去看看 executor

以下是產生 HTML 的範例。

.. code-block:: python

   from je_load_density import generate_html_report, start_test
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
    generate_html_report()


以下是產生 JSON 的範例。

.. code-block:: python

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

以下是產生 XML 的範例。

.. code-block:: python

    from je_load_density import generate_xml_report, start_test
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