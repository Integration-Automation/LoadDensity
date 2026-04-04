Report Generation API
=====================

Functions for generating test reports in HTML, JSON, and XML formats.

HTML Report
-----------

generate_html()
~~~~~~~~~~~~~~~

Generate HTML fragments for success and failure records.

.. code-block:: python

    def generate_html() -> Tuple[List[str], List[str]]

**Returns:** ``(success_list, failure_list)`` — Lists of HTML table strings.

**Raises:** ``LoadDensityHTMLException`` — If no test records exist.

generate_html_report()
~~~~~~~~~~~~~~~~~~~~~~

Generate a complete HTML report file.

.. code-block:: python

    def generate_html_report(html_name: str = "default_name") -> str

**Parameters:**

* ``html_name`` — Output file name (without extension). Creates ``{html_name}.html``.

**Returns:** File path of the generated HTML report.

JSON Report
-----------

generate_json()
~~~~~~~~~~~~~~~

Generate JSON data structures for success and failure records.

.. code-block:: python

    def generate_json() -> Tuple[Dict[str, dict], Dict[str, dict]]

**Returns:** ``(success_dict, failure_dict)``

* ``success_dict`` — Keys like ``"Success_Test1"``, values contain Method, test_url, name,
  status_code, text, content, headers
* ``failure_dict`` — Keys like ``"Failure_Test1"``, values contain Method, test_url, name,
  status_code, error

**Raises:** ``LoadDensityGenerateJsonReportException`` — If no test records exist.

generate_json_report()
~~~~~~~~~~~~~~~~~~~~~~

Generate JSON report files.

.. code-block:: python

    def generate_json_report(json_file_name: str = "default_name") -> Tuple[str, str]

**Parameters:**

* ``json_file_name`` — Output file name prefix. Creates ``{name}_success.json`` and
  ``{name}_failure.json``.

**Returns:** ``(success_path, failure_path)``

XML Report
----------

generate_xml()
~~~~~~~~~~~~~~

Generate XML strings for success and failure records.

.. code-block:: python

    def generate_xml() -> Tuple[str, str]

**Returns:** ``(success_xml_str, failure_xml_str)`` — XML strings wrapped under
``<xml_data>`` root element.

generate_xml_report()
~~~~~~~~~~~~~~~~~~~~~

Generate pretty-printed XML report files.

.. code-block:: python

    def generate_xml_report(xml_file_name: str = "default_name") -> Tuple[str, str]

**Parameters:**

* ``xml_file_name`` — Output file name prefix. Creates ``{name}_success.xml`` and
  ``{name}_failure.xml``.

**Returns:** ``(success_path, failure_path)``
