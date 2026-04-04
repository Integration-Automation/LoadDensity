Report Generation
=================

LoadDensity can generate test reports in three formats: **HTML**, **JSON**, and **XML**.
Reports are generated from the test records collected by the request hook during test execution.

.. note::

    Reports can only be generated after a test has been run. If no test records exist,
    a ``LoadDensityHTMLException`` or ``LoadDensityGenerateJsonReportException`` will be raised.

HTML Report
-----------

Generates a styled HTML file with tables showing success and failure records.

.. code-block:: python

    from je_load_density import generate_html_report

    # Generates "my_report.html"
    generate_html_report("my_report")

The HTML report includes:

* **Success records** — displayed in tables with aqua-colored headers, showing Method, URL,
  name, status_code, response text, content, and headers
* **Failure records** — displayed in tables with red-colored headers, showing Method, URL,
  name, status_code, and error message

To get raw HTML fragments without writing to a file:

.. code-block:: python

    from je_load_density import generate_html

    success_fragments, failure_fragments = generate_html()
    # success_fragments: List[str] — HTML table strings for each success record
    # failure_fragments: List[str] — HTML table strings for each failure record

JSON Report
-----------

Generates structured JSON files for programmatic consumption.

.. code-block:: python

    from je_load_density import generate_json_report

    # Generates "my_report_success.json" and "my_report_failure.json"
    success_path, failure_path = generate_json_report("my_report")

**Success JSON format:**

.. code-block:: json

    {
        "Success_Test1": {
            "Method": "GET",
            "test_url": "http://httpbin.org/get",
            "name": "/get",
            "status_code": "200",
            "text": "...",
            "content": "...",
            "headers": "..."
        },
        "Success_Test2": {}
    }

**Failure JSON format:**

.. code-block:: json

    {
        "Failure_Test1": {
            "Method": "POST",
            "test_url": "http://httpbin.org/status/500",
            "name": "/status/500",
            "status_code": "500",
            "error": "..."
        }
    }

To get raw JSON data structures without writing to a file:

.. code-block:: python

    from je_load_density import generate_json

    success_dict, failure_dict = generate_json()

XML Report
----------

Generates XML files for CI/CD integration.

.. code-block:: python

    from je_load_density import generate_xml_report

    # Generates "my_report_success.xml" and "my_report_failure.xml"
    success_path, failure_path = generate_xml_report("my_report")

The XML output is pretty-printed using ``xml.dom.minidom``. Each test record is wrapped
under an ``<xml_data>`` root element.

To get raw XML strings without writing to a file:

.. code-block:: python

    from je_load_density import generate_xml

    success_xml_str, failure_xml_str = generate_xml()

Using in JSON Scripts
---------------------

Report generation can be chained with test execution in JSON scripts:

.. code-block:: json

    [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 10,
            "spawn_rate": 5,
            "test_time": 5,
            "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
        }],
        ["LD_generate_html_report", {"html_name": "report"}],
        ["LD_generate_json_report", {"json_file_name": "report"}],
        ["LD_generate_xml_report", {"xml_file_name": "report"}]
    ]

Report Functions Summary
------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Function
     - Returns
     - Description
   * - ``generate_html()``
     - ``Tuple[List[str], List[str]]``
     - HTML fragments for success and failure records
   * - ``generate_html_report(html_name)``
     - ``str``
     - Write HTML report file, returns file path
   * - ``generate_json()``
     - ``Tuple[Dict, Dict]``
     - JSON dicts for success and failure records
   * - ``generate_json_report(json_file_name)``
     - ``Tuple[str, str]``
     - Write JSON report files, returns paths
   * - ``generate_xml()``
     - ``Tuple[str, str]``
     - XML strings for success and failure records
   * - ``generate_xml_report(xml_file_name)``
     - ``Tuple[str, str]``
     - Write XML report files, returns paths
