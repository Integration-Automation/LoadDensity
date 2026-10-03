Report Generation
=================

Overview
--------

LoadDensity can render six report formats from
``test_record_instance``: HTML, JSON, XML, CSV, JUnit XML, and a
percentile-summary JSON.

.. note::

    Reports require at least one record; calling a generator on an
    empty store raises ``LoadDensityHTMLException`` /
    ``LoadDensityGenerateJsonReportException``.

HTML
----

.. code-block:: python

    from je_load_density import generate_html_report
    generate_html_report("my_report")            # writes my_report.html

JSON (split by outcome)
-----------------------

.. code-block:: python

    from je_load_density import generate_json_report
    success_path, failure_path = generate_json_report("my_report")

XML (split by outcome)
----------------------

.. code-block:: python

    from je_load_density import generate_xml_report
    success_path, failure_path = generate_xml_report("my_report")

CSV (one row per request)
-------------------------

.. code-block:: python

    from je_load_density import generate_csv_report
    generate_csv_report("my_report")             # writes my_report.csv

Columns: ``outcome, Method, test_url, name, status_code,
response_time_ms, response_length, error``.

JUnit XML (CI-friendly)
-----------------------

.. code-block:: python

    from je_load_density import generate_junit_report
    generate_junit_report("loaddensity-junit")   # writes loaddensity-junit.xml

Each request becomes a ``<testcase>``; failures attach ``<failure>``
nodes carrying the error message. Compatible with Jenkins, GitHub
Actions test annotations, GitLab, etc.

Summary (percentiles)
---------------------

.. code-block:: python

    from je_load_density import generate_summary_report, build_summary

    summary = build_summary()                    # in-memory dict
    generate_summary_report("loaddensity-summary")

The summary contains totals, per-name counts, min / max / mean /
percentile (p50 / p90 / p95 / p99) latencies, and an overall block.
Useful for charting and regression checks across runs.

Percentile band charts
----------------------

Install the ``charts`` extra, then call ``generate_chart_report(report_name,
bucket_size_seconds=1.0, max_buckets=10000)``. Existing ``-latency.png`` /
``-rps.png`` filenames and ``latency`` / ``rps`` return keys are preserved.
Request-start buckets merge success/failure samples, plot a p50 line and
p50–p95 / p95–p99 bands, and calculate RPS using actual bucket duration.
Missing/invalid latency leaves a gap without discarding timed request counts.
The default history limit retains the newest 10,000 buckets.

Window percentiles select index ``round(p / 100 * (n - 1))`` with Python
ties-to-even rounding. Overall summary percentiles retain linear interpolation.
Latency statistics exclude negative/nonfinite/invalid measurements; totals retain
all requests. Qt and browser live charts use the same helper and retain 120 buckets.

Action JSON
-----------

Chain reports into a test::

    {"load_density": [
      ["LD_start_test", {...}],
      ["LD_generate_html_report",   {"html_name": "report"}],
      ["LD_generate_json_report",   {"json_file_name": "report"}],
      ["LD_generate_xml_report",    {"xml_file_name": "report"}],
      ["LD_generate_csv_report",    {"csv_name": "report"}],
      ["LD_generate_junit_report",  {"report_name": "report-junit"}],
      ["LD_generate_summary_report",{"report_name": "report-summary"}]
    ]}
