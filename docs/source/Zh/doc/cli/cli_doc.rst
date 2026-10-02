CLI 命令列介面
==============

LoadDensity 採子指令式 CLI。執行 ``python -m je_load_density --help`` 可查看完整介面。

子指令
------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 子指令
     - 用途
   * - ``run FILE``
     - 執行單一動作 JSON 檔。
   * - ``run-dir DIR``
     - 執行目錄下所有 ``.json``。
   * - ``run-str JSON``
     - 直接執行 inline JSON 字串（Windows 雙重編碼自動處理）。
   * - ``init PATH``
     - 建立新的專案骨架。
   * - ``serve``
     - 啟動硬化的 TCP 控制 socket server。

``run``
-------

.. code-block:: bash

    python -m je_load_density run smoke.json

``smoke.json`` 內容::

    {"load_density": [
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "user_count": 20, "spawn_rate": 10, "test_time": 30,
        "tasks": [{"method": "get", "request_url": "https://httpbin.org/get"}]
      }],
      ["LD_generate_summary_report", {"report_name": "smoke"}]
    ]}

``run-dir``
-----------

對目錄樹下所有 ``.json`` 動作檔執行::

    python -m je_load_density run-dir ./scenarios

``run-str``
-----------

Inline JSON（CI script 友善）::

    python -m je_load_density run-str '{"load_density":[["LD_summary",{}]]}'

``init``
--------

於 PATH 建立專案骨架::

    python -m je_load_density init ./my_load_test

``serve``
---------

啟動控制 socket server。詳見 :doc:`../socket_server/socket_server_doc`。

.. code-block:: bash

    python -m je_load_density serve \
        --host 0.0.0.0 --port 9940 \
        --framed --token "$LOAD_DENSITY_SOCKET_TOKEN" \
        --tls-cert /etc/loaddensity/server.crt \
        --tls-key /etc/loaddensity/server.key

舊式旗標
--------

之前版本的扁平旗標 ``-e/-d/-c/--execute_str`` 仍接受（在 ``--help`` 中隱藏），維持與 PyBreeze 等下游工具相容。新腳本應使用子指令。

煙霧測試與失敗結束碼
------------------------------

``run``、``run-dir``、``run-str`` 與舊執行旗標在動作（包含 SLA gate）失敗時回傳非零 exit code。單一檔案的動作仍依序執行並產生原有報告；Python executor 的回傳格式保持相容。基本安裝包含原生 async benchmark 所需的 httpx，HTTP/2 需要 ``http2`` extra。

在 checkout 執行 ``python -m unittest discover -s test/smoke -p "test_*.py"``。標準函式庫 harness 啟動獨立本機 HTTP 服務與子行程，驗證實際 Locust／async 請求、summary／JSON／JUnit、SQLite、SLA 失敗、dashboard JSON／SSE 與 MCP 初始化。Docker 在原始碼樹外使用同一 harness 驗證已安裝 wheel。
