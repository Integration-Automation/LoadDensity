產生報告
========

概觀
----

LoadDensity 可從 ``test_record_instance`` 產生六種報告：HTML、JSON、XML、CSV、JUnit XML、百分位摘要 JSON。

.. note::

    報告需要至少一筆紀錄；對空 store 呼叫產生器會拋出 ``LoadDensityHTMLException`` / ``LoadDensityGenerateJsonReportException``。

HTML
----

.. code-block:: python

    from je_load_density import generate_html_report
    generate_html_report("my_report")            # 寫出 my_report.html

JSON（依結果分檔）
------------------

.. code-block:: python

    from je_load_density import generate_json_report
    success_path, failure_path = generate_json_report("my_report")

XML（依結果分檔）
-----------------

.. code-block:: python

    from je_load_density import generate_xml_report
    success_path, failure_path = generate_xml_report("my_report")

CSV（每筆請求一列）
-------------------

.. code-block:: python

    from je_load_density import generate_csv_report
    generate_csv_report("my_report")             # 寫出 my_report.csv

欄位：``outcome, Method, test_url, name, status_code, response_time_ms, response_length, error``。

JUnit XML（CI 友善）
--------------------

.. code-block:: python

    from je_load_density import generate_junit_report
    generate_junit_report("loaddensity-junit")   # 寫出 loaddensity-junit.xml

每筆請求變成 ``<testcase>``；失敗附上 ``<failure>`` 節點。可餵 Jenkins、GitHub Actions、GitLab 等。

Summary（百分位）
-----------------

.. code-block:: python

    from je_load_density import generate_summary_report, build_summary

    summary = build_summary()                    # 記憶體 dict
    generate_summary_report("loaddensity-summary")

包含 totals、per-name 計數、min / max / mean / 百分位（p50 / p90 / p95 / p99）延遲與整體區塊。便於繪圖與跨次回歸檢查。

動作 JSON
---------

把報告串入測試::

    {"load_density": [
      ["LD_start_test", {...}],
      ["LD_generate_html_report",   {"html_name": "report"}],
      ["LD_generate_json_report",   {"json_file_name": "report"}],
      ["LD_generate_xml_report",    {"xml_file_name": "report"}],
      ["LD_generate_csv_report",    {"csv_name": "report"}],
      ["LD_generate_junit_report",  {"report_name": "report-junit"}],
      ["LD_generate_summary_report",{"report_name": "report-summary"}]
    ]}
