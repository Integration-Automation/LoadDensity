====================================
LoadDensity 繁體中文手冊
====================================

繁中手冊依照讀者使用順序分為十二章:安裝 → 執行壓測 → 撰寫動作腳本 →
韌性強化 → 擴展 → 整合。可使用左側目次,或直接跳到下方章節。

.. contents:: 本頁目次
   :local:
   :depth: 1

----

.. _zh-getting-started:

第 1 章 — 入門
==============

安裝 LoadDensity、執行第一次壓測,並建立專案骨架。

.. toctree::
    :maxdepth: 2
    :caption: 入門

    doc/installation/installation_doc
    doc/getting_started/getting_started_doc
    doc/create_project/create_project_doc

.. _zh-core-api:

第 2 章 — 核心 API
==================

面向 Locust 的封裝:環境、Runner、使用者代理。

.. toctree::
    :maxdepth: 2
    :caption: 核心 API

    doc/architecture/architecture_doc
    doc/start_test/start_test_doc
    doc/locust_env/locust_env_doc

.. _zh-actions:

第 3 章 — 動作撰寫與執行
========================

組合 JSON 動作腳本、參數化資料、建立情境流程,串接測試後 callback。

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

協定驅動程式:HTTP、FastHttp、Async HTTP/2、WebSocket、SSE、gRPC
(unary + 串流)、MQTT、原生 TCP/UDP、SQL、Redis、Kafka、MongoDB。

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

產生 HTML / JSON / XML / CSV / JUnit / 百分位摘要 / chart 報告,將
指標送至 Prometheus、InfluxDB、OTLP 或 Datadog DogStatsD,並把即時
進度推送到瀏覽器。

.. toctree::
    :maxdepth: 2
    :caption: 報告

    doc/generate_report/generate_report_doc
    doc/metrics/metrics_doc
    doc/test_record/test_record_doc
    doc/live_dashboard/live_dashboard_doc
    doc/notifiers/notifiers_doc

.. _zh-orchestration:

第 6 章 — 編排與擴展
====================

執行分散式 master/worker 群集、透過參數解析器共享狀態、依擷取變數
控制執行流程,並以內建 load shape 引導 ramp。

.. toctree::
    :maxdepth: 2
    :caption: 編排

    doc/distributed/distributed_doc

.. _zh-reliability:

第 7 章 — 可靠度
================

自適應重試、失敗預算 / circuit breaker、網路條件、process supervisor —
讓 CI 無人值守也能安全執行。

.. toctree::
    :maxdepth: 2
    :caption: 可靠度

    doc/reliability/reliability_doc

.. _zh-recording-data:

第 8 章 — 錄製、資料與匯入器
============================

將 HAR、Postman v2.1、OpenAPI 3.x、cURL、k6、JMeter JMX 轉成可執行
動作 JSON,將測試紀錄持久化到 SQLite,並比對歷次執行結果。

.. toctree::
    :maxdepth: 2
    :caption: 錄製、資料與匯入器

    doc/har_import/har_import_doc
    doc/importers/importers_doc
    doc/sqlite_persistence/sqlite_persistence_doc

.. _zh-auth:

第 9 章 — Auth
==============

含 cache 的 OAuth2 token helper、JWT 簽發(HS / RS)、AWS Signature
v4,以及所有 HTTP user template 都支援的 mTLS client-cert。

.. toctree::
    :maxdepth: 2
    :caption: Auth

    doc/auth/auth_doc

.. _zh-tooling:

第 10 章 — 工具、CLI 與診斷
===========================

命令列子指令、硬化的控制 socket server、traceback 中可能出現的例外
階層,以及編輯器 / CI 整合:linter、schema、LSP、VS Code 擴充套件、
GitHub Action、pre-commit。

.. toctree::
    :maxdepth: 2
    :caption: 工具

    doc/cli/cli_doc
    doc/socket_server/socket_server_doc
    doc/exception/exception_doc
    doc/editor_integration/editor_integration_doc

.. _zh-integrations:

第 11 章 — 整合
===============

選用的 GUI、可讓 Claude 驅動 LoadDensity 的 **MCP** server。

.. toctree::
    :maxdepth: 2
    :caption: 整合

    doc/gui/gui_doc
    doc/mcp_claude/mcp_claude_doc

.. _zh-reference:

第 12 章 — API Reference
========================

自動產生的 Python API reference。

.. toctree::
    :maxdepth: 2
    :caption: 參考

    doc/api_reference/api_reference
