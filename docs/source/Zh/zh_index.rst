====================================
LoadDensity 繁體中文手冊
====================================

繁體中文手冊依照讀者使用順序分為十章：安裝 → 執行壓測 → 撰寫動作腳本 → 擴展 → 整合。可使用左側目次，或直接跳到下方章節。

.. contents:: 本頁目次
   :local:
   :depth: 1

----

.. _zh-getting-started:

第 1 章 — 入門
==============

安裝 LoadDensity、執行第一次壓測，並建立專案骨架。

.. toctree::
    :maxdepth: 2
    :caption: 入門

    doc/installation/installation_doc
    doc/getting_started/getting_started_doc
    doc/create_project/create_project_doc

.. _zh-core-api:

第 2 章 — 核心 API
==================

面向 Locust 的封裝：環境、Runner、使用者代理。讀過這章後，整個框架就不再神秘。

.. toctree::
    :maxdepth: 2
    :caption: 核心 API

    doc/architecture/architecture_doc
    doc/start_test/start_test_doc
    doc/locust_env/locust_env_doc

.. _zh-actions:

第 3 章 — 動作撰寫與執行
========================

組合 JSON 動作腳本、參數化資料、建立情境流程，串接測試後 callback。

.. toctree::
    :maxdepth: 2
    :caption: 動作

    doc/action_executor/action_executor_doc
    doc/parameter_resolver/parameter_resolver_doc
    doc/scenarios/scenarios_doc
    doc/assertions/assertions_doc
    doc/callback/callback_doc
    doc/package_manager/package_manager_doc

.. _zh-user-templates:

第 4 章 — 使用者模板
====================

協定驅動程式：HTTP、FastHttp、WebSocket、gRPC、MQTT，以及原生 TCP/UDP。每個模板皆以 Locust 使用者註冊，採用相同的 task 契約。

.. toctree::
    :maxdepth: 2
    :caption: 使用者模板

    doc/http_users/http_users_doc
    doc/websocket_user/websocket_user_doc
    doc/grpc_user/grpc_user_doc
    doc/mqtt_user/mqtt_user_doc
    doc/socket_user/socket_user_doc

.. _zh-reporting:

第 5 章 — 報告與可觀測性
========================

產生 HTML / JSON / XML / CSV / JUnit / 百分位摘要報告，將指標送至 Prometheus、InfluxDB，或任何 OTLP 後端。

.. toctree::
    :maxdepth: 2
    :caption: 報告

    doc/generate_report/generate_report_doc
    doc/metrics/metrics_doc
    doc/test_record/test_record_doc

.. _zh-orchestration:

第 6 章 — 編排與擴展
====================

執行分散式 master/worker 群集、透過參數解析器共享狀態、依擷取變數控制執行流程。

.. toctree::
    :maxdepth: 2
    :caption: 編排

    doc/distributed/distributed_doc

.. _zh-recording-data:

第 7 章 — 錄製與資料
====================

將真實瀏覽流量（HAR）轉換為可執行的動作 JSON，將測試紀錄持久化到 SQLite，並比對歷次執行結果。

.. toctree::
    :maxdepth: 2
    :caption: 錄製與資料

    doc/har_import/har_import_doc
    doc/sqlite_persistence/sqlite_persistence_doc

.. _zh-tooling:

第 8 章 — 工具、CLI 與診斷
==========================

命令列子指令、硬化的控制 socket server，以及 traceback 中可能出現的例外階層。

.. toctree::
    :maxdepth: 2
    :caption: 工具

    doc/cli/cli_doc
    doc/socket_server/socket_server_doc
    doc/exception/exception_doc

.. _zh-integrations:

第 9 章 — 整合
==============

選用的 GUI、可讓 Claude 驅動 LoadDensity 的 **Model Context Protocol (MCP)** server，以及下游 PyBreeze IDE 整合。

.. toctree::
    :maxdepth: 2
    :caption: 整合

    doc/gui/gui_doc
    doc/mcp_claude/mcp_claude_doc

.. _zh-reference:

第 10 章 — API Reference
========================

自動產生的 Python API reference。

.. toctree::
    :maxdepth: 2
    :caption: 參考

    doc/api_reference/api_reference
