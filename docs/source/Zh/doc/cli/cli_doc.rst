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
