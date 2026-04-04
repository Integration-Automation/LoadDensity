報告產生
========

LoadDensity 可以產生三種格式的測試報告：**HTML**、**JSON** 和 **XML**。
報告是根據測試執行期間由 request hook 收集的測試紀錄產生的。

.. note::

    報告只能在測試執行後產生。若不存在測試紀錄，會拋出
    ``LoadDensityHTMLException`` 或 ``LoadDensityGenerateJsonReportException``。

HTML 報告
---------

產生帶有樣式的 HTML 檔案，以表格顯示成功與失敗紀錄。

.. code-block:: python

    from je_load_density import generate_html_report

    # 產生 "my_report.html"
    generate_html_report("my_report")

HTML 報告包含：

* **成功紀錄** — 以青色表頭的表格顯示，包含 Method、URL、name、status_code、
  回應內文、content 和 headers
* **失敗紀錄** — 以紅色表頭的表格顯示，包含 Method、URL、name、status_code 和錯誤訊息

若要取得原始 HTML 片段而不寫入檔案：

.. code-block:: python

    from je_load_density import generate_html

    success_fragments, failure_fragments = generate_html()
    # success_fragments: List[str] — 每筆成功紀錄的 HTML 表格字串
    # failure_fragments: List[str] — 每筆失敗紀錄的 HTML 表格字串

JSON 報告
---------

產生結構化的 JSON 檔案，供程式化使用。

.. code-block:: python

    from je_load_density import generate_json_report

    # 產生 "my_report_success.json" 和 "my_report_failure.json"
    success_path, failure_path = generate_json_report("my_report")

**成功 JSON 格式：**

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

**失敗 JSON 格式：**

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

若要取得原始 JSON 資料結構而不寫入檔案：

.. code-block:: python

    from je_load_density import generate_json

    success_dict, failure_dict = generate_json()

XML 報告
--------

產生 XML 檔案，適用於 CI/CD 整合。

.. code-block:: python

    from je_load_density import generate_xml_report

    # 產生 "my_report_success.xml" 和 "my_report_failure.xml"
    success_path, failure_path = generate_xml_report("my_report")

XML 輸出使用 ``xml.dom.minidom`` 進行格式化。每筆測試紀錄包裝在 ``<xml_data>`` 根節點下。

若要取得原始 XML 字串而不寫入檔案：

.. code-block:: python

    from je_load_density import generate_xml

    success_xml_str, failure_xml_str = generate_xml()

在 JSON 腳本中使用
--------------------

報告產生可以與測試執行在 JSON 腳本中串連：

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

報告函式總覽
------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - 函式
     - 回傳值
     - 說明
   * - ``generate_html()``
     - ``Tuple[List[str], List[str]]``
     - 成功與失敗紀錄的 HTML 片段
   * - ``generate_html_report(html_name)``
     - ``str``
     - 寫入 HTML 報告檔案，回傳檔案路徑
   * - ``generate_json()``
     - ``Tuple[Dict, Dict]``
     - 成功與失敗紀錄的 JSON 字典
   * - ``generate_json_report(json_file_name)``
     - ``Tuple[str, str]``
     - 寫入 JSON 報告檔案，回傳路徑
   * - ``generate_xml()``
     - ``Tuple[str, str]``
     - 成功與失敗紀錄的 XML 字串
   * - ``generate_xml_report(xml_file_name)``
     - ``Tuple[str, str]``
     - 寫入 XML 報告檔案，回傳路徑
