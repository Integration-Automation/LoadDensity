MCP Server（給 Claude）
=======================

概觀
----

LoadDensity 內含一個 `Model Context Protocol <https://modelcontextprotocol.io/>`_ server，將框架功能以 MCP 工具暴露。Claude（Desktop、Code 或任何 MCP 客戶端）可藉此驅動壓力測試、產生報告、匯入 HAR、檢視持久化資料，無需離開對話。

安裝
----

.. code-block:: bash

    pip install "je_load_density[mcp]"

啟動
----

.. code-block:: bash

    python -m je_load_density.mcp_server

Server 透過 stdio 講 MCP。請接到你選用的客戶端（Claude Desktop ``claude_desktop_config.json``、Claude Code 等）：

.. code-block:: json

    {
      "mcpServers": {
        "loaddensity": {
          "command": "python",
          "args": ["-m", "je_load_density.mcp_server"]
        }
      }
    }

提供的工具
----------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Tool
     - 用途
   * - ``load_density.run_test``
     - 跑一個 Locust 壓測（HTTP / WS / gRPC / MQTT / Socket）。
   * - ``load_density.run_action_json``
     - 執行動作 JSON 文件。
   * - ``load_density.create_project``
     - 在 PATH 建立專案骨架。
   * - ``load_density.list_executor_commands``
     - 列出 executor 註冊的所有 ``LD_*`` 指令。
   * - ``load_density.import_har``
     - 將 HAR 檔轉成可執行的動作 JSON。
   * - ``load_density.generate_reports``
     - 產生 HTML / JSON / XML / CSV / JUnit / summary 任意組合。
   * - ``load_density.summary``
     - 回傳彙整統計（totals、per-name p50/p90/p95/p99）。
   * - ``load_density.persist_records``
     - 將目前紀錄寫入 SQLite 資料庫。
   * - ``load_density.list_runs``
     - 列出近期持久化的 runs。
   * - ``load_density.fetch_run``
     - 取出某次 run 的所有紀錄。
   * - ``load_density.clear_records``
     - 開始新一輪前清除記憶體中的紀錄。
