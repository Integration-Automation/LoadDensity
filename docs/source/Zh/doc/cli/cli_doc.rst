命令列介面（CLI）
==================

LoadDensity 提供完整的命令列介面，透過 ``python -m je_load_density`` 使用。

CLI 參數
--------

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - 參數
     - 簡寫
     - 說明
   * - ``--execute_file``
     - ``-e``
     - 執行單一 JSON 腳本檔案
   * - ``--execute_dir``
     - ``-d``
     - 執行目錄下所有 JSON 檔案
   * - ``--execute_str``
     - —
     - 執行行內 JSON 字串
   * - ``--create_project``
     - ``-c``
     - 建置新專案（包含模板）

執行單一 JSON 檔案
--------------------

執行定義在單一 JSON 關鍵字檔案中的測試：

.. code-block:: bash

    python -m je_load_density -e test_scenario.json

JSON 檔案應遵循動作列表格式：

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

執行目錄下所有 JSON 檔案
--------------------------

遞迴執行指定目錄下所有 JSON 關鍵字檔案：

.. code-block:: bash

    python -m je_load_density -d ./test_scripts/

此命令會掃描目錄中所有 ``.json`` 檔案，依序執行。

執行行內 JSON 字串
--------------------

直接以字串形式執行 JSON 動作列表：

.. code-block:: bash

    python -m je_load_density --execute_str '[["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}, "user_count": 10, "spawn_rate": 5, "test_time": 5, "tasks": {"get": {"request_url": "http://httpbin.org/get"}}}]]'

.. note::

    在 **Windows** 平台上，行內 JSON 字串會因為 shell 跳脫字元差異而自動進行雙重解析。
    CLI 會自動處理此差異。

建立專案
--------

建置包含關鍵字模板與執行器腳本的新專案：

.. code-block:: bash

    python -m je_load_density -c MyProject

產生的專案目錄結構：

.. code-block:: text

    MyProject/
    └── LoadDensity/
        ├── keyword/
        │   ├── keyword1.json
        │   └── keyword2.json
        └── executor/
            ├── executor_one_file.py
            └── executor_folder.py

錯誤處理
--------

若未提供有效參數，CLI 會拋出 ``LoadDensityTestExecuteException`` 並以結束碼 1 退出。
所有錯誤訊息會輸出至 stderr。
