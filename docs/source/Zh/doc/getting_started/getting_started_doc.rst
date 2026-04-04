開始使用
========

本指南將帶您了解如何使用 LoadDensity 執行第一個負載測試。

使用者類型
----------

LoadDensity 支援兩種 Locust 使用者類型：

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - 使用者類型鍵值
     - Locust 類別
     - 說明
   * - ``fast_http_user``
     - ``FastHttpUser``
     - 使用 ``geventhttpclient``，效能較高。建議大多數情況使用。
   * - ``http_user``
     - ``HttpUser``
     - 使用 Python ``requests`` 函式庫。相容性較佳，效能較低。

支援的 HTTP 方法
-----------------

LoadDensity 支援以下 HTTP 方法：

* ``get``
* ``post``
* ``put``
* ``patch``
* ``delete``
* ``head``
* ``options``

使用 Python API 執行測試
-------------------------

最簡單的方式是呼叫 ``start_test()``：

.. code-block:: python

    from je_load_density import start_test

    result = start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=10,
        tasks={
            "get": {"request_url": "http://httpbin.org/get"},
            "post": {"request_url": "http://httpbin.org/post"},
        }
    )

``start_test()`` 參數說明
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - 參數
     - 類型
     - 預設值
     - 說明
   * - ``user_detail_dict``
     - ``dict``
     - （必填）
     - 使用者類型設定。``{"user": "fast_http_user"}`` 或 ``{"user": "http_user"}``
   * - ``user_count``
     - ``int``
     - ``50``
     - 模擬使用者總數
   * - ``spawn_rate``
     - ``int``
     - ``10``
     - 每秒生成使用者數量
   * - ``test_time``
     - ``int`` 或 ``None``
     - ``60``
     - 測試持續時間（秒）。傳入 ``None`` 則無限制
   * - ``web_ui_dict``
     - ``dict`` 或 ``None``
     - ``None``
     - 啟用 Locust Web UI。例如 ``{"host": "127.0.0.1", "port": 8089}``

回傳值
~~~~~~

``start_test()`` 回傳一個測試設定摘要字典：

.. code-block:: python

    {
        "user_detail": {"user": "fast_http_user"},
        "user_count": 50,
        "spawn_rate": 10,
        "test_time": 10,
        "web_ui": None,
    }

啟用 Locust Web UI
-------------------

若要透過 Locust Web UI 即時監控測試：

.. code-block:: python

    from je_load_density import start_test

    result = start_test(
        user_detail_dict={"user": "http_user"},
        user_count=100,
        spawn_rate=20,
        test_time=30,
        web_ui_dict={"host": "127.0.0.1", "port": 8089},
        tasks={
            "get": {"request_url": "http://httpbin.org/get"},
        }
    )

然後在瀏覽器開啟 ``http://127.0.0.1:8089`` 即可查看即時統計資料。

使用 JSON 腳本檔案執行測試
----------------------------

可以將測試情境定義為 JSON 檔案，無需撰寫 Python 程式碼即可執行。

建立 ``test_scenario.json`` 檔案：

.. code-block:: json

    [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 50,
            "spawn_rate": 10,
            "test_time": 5,
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }]
    ]

從 Python 執行：

.. code-block:: python

    from je_load_density import execute_action, read_action_json

    execute_action(read_action_json("test_scenario.json"))

JSON 腳本格式
~~~~~~~~~~~~~~

每個 JSON 腳本是一個動作陣列。每個動作是一個列表：

* 使用關鍵字參數：``["action_name", {"param1": "value1"}]``
* 使用位置參數：``["action_name", ["arg1", "arg2"]]``
* 無參數：``["action_name"]``

串連多個動作
~~~~~~~~~~~~

多個動作可以在單一 JSON 檔案中串連。例如，執行測試並自動產生報告：

.. code-block:: json

    [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 10,
            "spawn_rate": 5,
            "test_time": 5,
            "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
        }],
        ["LD_generate_html_report", {"html_name": "my_report"}],
        ["LD_generate_json_report", {"json_file_name": "my_report"}],
        ["LD_generate_xml_report", {"xml_file_name": "my_report"}]
    ]

字典格式 JSON
~~~~~~~~~~~~~~

JSON 腳本也可以用字典包裝，使用 ``"load_density"`` 鍵值：

.. code-block:: json

    {
        "load_density": [
            ["LD_start_test", {
                "user_detail_dict": {"user": "fast_http_user"},
                "user_count": 10,
                "spawn_rate": 5,
                "test_time": 5,
                "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
            }]
        ]
    }

專案建置
--------

LoadDensity 可以自動產生專案目錄結構，包含關鍵字模板與執行器腳本：

.. code-block:: python

    from je_load_density import create_project_dir

    create_project_dir(project_path="./my_tests", parent_name="LoadDensity")

或透過 CLI：

.. code-block:: bash

    python -m je_load_density -c ./my_tests

產生的結構如下：

.. code-block:: text

    my_tests/
    └── LoadDensity/
        ├── keyword/
        │   ├── keyword1.json    # FastHttpUser 測試模板
        │   └── keyword2.json    # HttpUser 測試模板
        └── executor/
            ├── executor_one_file.py   # 執行單一關鍵字檔案
            └── executor_folder.py     # 執行 keyword/ 下所有檔案

* ``keyword1.json`` — 使用 ``fast_http_user`` 的模板，包含範例 GET/POST 任務
* ``keyword2.json`` — 使用 ``http_user`` 的模板，包含範例 GET/POST 任務
* ``executor_one_file.py`` — 執行 ``keyword1.json`` 的 Python 腳本
* ``executor_folder.py`` — 執行 ``keyword/`` 目錄下所有 JSON 檔案的 Python 腳本
