Generate Report
----

* Generate Report can generate reports in the following formats:
 * HTML
 * JSON
 * XML

* Generate Report is mainly used to record and confirm which steps were executed and whether they were successful or not.
* The following example is used with keywords and an executor. If you don't understand, please first take a look at the executor.

Here's an example of generating an HTML report.

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

Here's an example of generating an JSON report.

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


Here's an example of generating an XML report.

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