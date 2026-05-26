Report Generation API
=====================

Six report formats render from ``test_record_instance``: HTML, JSON
(split by outcome), XML (split by outcome), CSV, JUnit XML, and a
percentile-summary JSON.

.. note::

    Every generator raises if the record store is empty. Catch
    ``LoadDensityHTMLException`` (HTML), ``LoadDensityGenerateJsonReportException``
    (JSON / summary / CSV / JUnit), or ``XMLException`` (XML).

HTML
----

generate_html()
~~~~~~~~~~~~~~~

.. code-block:: python

    def generate_html() -> Tuple[List[str], List[str]]

Returns ``(success_list, failure_list)`` — HTML table fragments for
each outcome.

generate_html_report()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def generate_html_report(html_name: str = "default_name") -> str

Writes ``{html_name}.html``; returns the file path.

JSON (split by outcome)
-----------------------

generate_json()
~~~~~~~~~~~~~~~

.. code-block:: python

    def generate_json() -> Tuple[Dict[str, dict], Dict[str, dict]]

Returns ``(success_dict, failure_dict)``.

generate_json_report()
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def generate_json_report(json_file_name: str = "default_name") -> Tuple[str, str]

Writes ``{name}_success.json`` + ``{name}_failure.json``; returns
``(success_path, failure_path)``.

XML (split by outcome)
----------------------

generate_xml()
~~~~~~~~~~~~~~

.. code-block:: python

    def generate_xml() -> Tuple[str, str]

Returns ``(success_xml_str, failure_xml_str)``; both wrapped under an
``<xml_data>`` root.

generate_xml_report()
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def generate_xml_report(xml_file_name: str = "default_name") -> Tuple[str, str]

Writes ``{name}_success.xml`` + ``{name}_failure.xml`` (pretty
printed).

CSV (one row per request)
-------------------------

.. code-block:: python

    def generate_csv_report(csv_name: str = "default_name") -> str

Writes ``{csv_name}.csv``. Columns: ``outcome, Method, test_url, name,
status_code, response_time_ms, response_length, error``.

JUnit XML (CI-friendly)
-----------------------

.. code-block:: python

    def generate_junit_report(report_name: str = "default_name-junit") -> str

Writes ``{report_name}.xml``. Each request becomes a ``<testcase>``;
failures attach ``<failure>`` nodes carrying the error message.

Summary (percentiles)
---------------------

.. code-block:: python

    def build_summary() -> dict
    def generate_summary_report(report_name: str = "default_name-summary") -> str

``build_summary`` returns the in-memory dict; ``generate_summary_report``
writes ``{report_name}.json``. The dict contains totals, failure rate,
per-name counts, min / max / mean, and percentile (p50 / p90 / p95 /
p99) latencies. Useful for charting and regression checks.

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Command
     - Writes
   * - ``LD_generate_html_report``
     - ``<base>.html``
   * - ``LD_generate_json_report``
     - ``<base>_success.json`` + ``<base>_failure.json``
   * - ``LD_generate_xml_report``
     - ``<base>_success.xml`` + ``<base>_failure.xml``
   * - ``LD_generate_csv_report``
     - ``<base>.csv``
   * - ``LD_generate_junit_report``
     - ``<base>.xml``
   * - ``LD_generate_summary_report``
     - ``<base>.json`` (per-name percentiles)
   * - ``LD_summary``
     - Returns the summary dict in memory.
