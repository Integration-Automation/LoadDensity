架構
====

概觀
----

LoadDensity 是 Locust 之上的薄封裝,額外加上 JSON 驅動的動作 executor、
多協定 user template 註冊、情境流程、資料參數化、可觀測性 sink、
生產等級可靠度控制(自適應重試、失敗預算、網路條件)、即時 web
dashboard、Slack/Teams 通知、OAuth2/JWT/SigV4 Auth helper,以及讓
Claude 端對端驅動的 MCP 控制 plane。

相依方向永遠是「動作層 → Locust」,絕不反向 — 你的動作 JSON 描述要做
什麼,executor 將每個指令對應到 Python callable,Locust 負責跑出實際
壓力。

系統總覽
--------

.. mermaid::

    flowchart LR
      subgraph Authoring
        A1["Action JSON 檔案"]
        A2["程式呼叫 start_test"]
        A3["HAR / Postman / OpenAPI /<br/>cURL / k6 / JMeter 匯入"]
        A4["MCP / Claude"]
      end

      subgraph Core
        EXE["Action Executor<br/>event_dict (LD_*)"]
        RES["Parameter Resolver<br/>${var} / ${env} / ${csv} / ${db} / ${faker}"]
        REC["test_record_instance"]
        REL["Reliability<br/>retry · failure budget · conditioner"]
      end

      subgraph Runners
        LOC["Locust local"]
        MAS["Locust master"]
        WRK["Locust worker"]
      end

      subgraph Templates
        HTTP["HTTP / FastHttp / Async-HTTP2"]
        WS["WebSocket / SSE"]
        GRPC["gRPC(unary + 串流)"]
        MQ["MQTT / Kafka"]
        SOCK["原生 TCP/UDP"]
        DATA["SQL / Redis / MongoDB"]
      end

      subgraph Outputs
        REP["報告<br/>HTML/JSON/XML/CSV/JUnit/Summary/Chart"]
        EXP["Exporter<br/>Prometheus · InfluxDB · OTel · StatsD"]
        DASH["即時 Dashboard(SSE)"]
        NOT["通知<br/>Slack · Teams"]
        SQL["SQLite 持久化 + 跨次 diff"]
      end

      A1 --> EXE
      A2 --> EXE
      A3 --> A1
      A4 --> EXE
      EXE --> RES
      EXE --> REL
      EXE --> LOC
      EXE --> MAS
      EXE --> WRK
      LOC --> HTTP & WS & GRPC & MQ & SOCK & DATA
      MAS --> WRK
      WRK --> HTTP & WS & GRPC & MQ & SOCK & DATA
      HTTP & WS & GRPC & MQ & SOCK & DATA --> REC
      REC --> REP & EXP & DASH & NOT & SQL

動作生命週期
------------

.. mermaid::

    flowchart LR
      IN["Action<br/>[cmd, args_or_kwargs]"] --> DISP["event_dict[cmd]"]
      DISP -- "LD_start_test" --> SEED["依 variables / csv / db<br/>填入 resolver"]
      SEED --> PICK["挑選 user 模板<br/>(_USER_REGISTRY)"]
      PICK --> ENV["prepare_env<br/>(local / master / worker · load_shape)"]
      ENV --> RUN["Locust runner tick"]
      RUN --> THR["throttle.rps 限流"]
      THR --> COND["網路條件<br/>(latency / jitter / loss)"]
      COND --> EXPAND["參數解析器<br/>展開 task ${...}"]
      EXPAND --> RETRY["per-task retry<br/>(transient / flaky / permanent)"]
      RETRY --> EXEC["execute_task"]
      EXEC -- 回應 --> ASSERT["assertions + extractors"]
      ASSERT --> EVT["Locust request 事件"]
      EVT --> REC["test_record_instance.append"]
      EVT --> FB["failure_budget · 超標即 trip"]

User 派發
---------

.. mermaid::

    flowchart TB
      CMD["start_test(user_detail_dict={...})"] --> KEY{"user key?"}
      KEY -- "fast_http_user(預設)" --> FH["FastHttpUserWrapper"]
      KEY -- "http_user" --> H["HttpUserWrapper(requests)"]
      KEY -- "async_http_user" --> AH["AsyncHttpUserWrapper<br/>(httpx, HTTP/2 可選)"]
      KEY -- "websocket_user" --> WS["WebSocketUserWrapper"]
      KEY -- "sse_user" --> SS["SseUserWrapper"]
      KEY -- "grpc_user" --> G["GrpcUserWrapper<br/>(unary + 串流)"]
      KEY -- "mqtt_user" --> M["MqttUserWrapper"]
      KEY -- "kafka_user" --> K["KafkaUserWrapper"]
      KEY -- "socket_user" --> S["SocketUserWrapper"]
      KEY -- "sql_user" --> SQ["SqlUserWrapper"]
      KEY -- "redis_user" --> R["RedisUserWrapper"]
      KEY -- "mongo_user" --> MO["MongoUserWrapper"]
      FH & H & AH & WS & SS & G & M & K & S & SQ & R & MO --> SC["scenario_runner"]
      SC --> RX["request_executor.execute_task"]

模組地圖
--------

.. code-block:: text

    je_load_density/
    ├── __init__.py                       # 公開 API(108 條)
    ├── __main__.py                       # CLI: run / run-dir / run-str / init / serve
    ├── action_lsp/                       # 動作 JSON 的 LSP 伺服器
    ├── mcp_server/                       # MCP server(13 個給 Claude 的工具)
    ├── tools/                            # CLI 工具(pre-commit linter)
    ├── gui/                              # 選用 PySide6 前端
    ├── utils/
    │   ├── auth/                         # OAuth2 / JWT / AWS SigV4
    │   ├── callback/                     # callback_executor
    │   ├── ci_annotations/               # GitHub Actions 註解
    │   ├── dashboard/                    # 即時 web dashboard (SSE)
    │   ├── exception/                    # LoadDensity* 例外階層
    │   ├── executor/                     # Executor · event_dict · 安全 builtins
    │   ├── file_process/                 # 目錄走訪 · 專案 scaffold
    │   ├── generate_report/              # HTML / JSON / XML / CSV / JUnit / Summary / Chart
    │   ├── graphql/                      # GraphQL helper
    │   ├── json/                         # JSON 讀寫
    │   ├── linter/                       # Action JSON linter
    │   ├── load_shapes/                  # Stages / Spike / Soak
    │   ├── logging/                      # 已設定 logger
    │   ├── metrics/                      # Prometheus · InfluxDB · OTel · DogStatsD
    │   ├── notifier/                     # Slack · Teams
    │   ├── package_manager/              # 動態套件載入
    │   ├── parameterization/             # var / env / csv / db / faker
    │   ├── project/                      # 專案範本
    │   ├── recording/                    # HAR / Postman / OpenAPI / cURL / k6 / JMeter
    │   ├── regression/                   # 跨次 diff
    │   ├── reliability/                  # adaptive_retry / failure_budget /
    │   │                                 # network_conditioner / process_supervisor
    │   ├── schema/                       # JSON Schema 匯出
    │   ├── sla/                          # SLA gate
    │   ├── socket_server/                # 長度框架 TCP 控制 plane(+TLS+token)
    │   ├── test_record/                  # 記憶體紀錄 + SQLite 持久化
    │   ├── throttle/                     # 共享 token-bucket
    │   └── xml/                          # defusedxml XML helper
    └── wrapper/
        ├── create_locust_env/            # prepare_env / create_env(local/master/worker + shape)
        ├── event/                        # request_hook(Locust 事件 → 紀錄)
        ├── proxy/                        # 各協定 task store(12 種 user)
        └── user_template/                # 12 種 Locust user + scenario_runner + request_executor
    load_density_driver/                  # 獨立 driver 建置
    examples/                             # 12 個可執行 recipe
    docker/                               # httpbin / mosquitto / redis / kafka / prometheus
    editors/vscode/                       # VS Code 擴充套件骨架
    action.yml                            # composite GitHub Action
    .pre-commit-hooks.yaml                # pre-commit 入口
    test/                                 # pytest 測試(225 個)
    docs/                                 # Sphinx 文件(En / Zh / API)

模組職責
--------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 模組
     - 用途
   * - ``je_load_density.utils.executor``
     - ``Executor`` 類別、派發表(``LD_*``)、安全 builtin 閘門。
   * - ``je_load_density.utils.parameterization``
     - ``${var/env/csv/db/faker}`` 與內建 helper。
   * - ``je_load_density.utils.recording``
     - HAR / Postman / OpenAPI / cURL / k6 / JMeter 匯入器。
   * - ``je_load_density.utils.metrics``
     - Prometheus、InfluxDB、OTel、DogStatsD sink。
   * - ``je_load_density.utils.test_record``
     - 記憶體紀錄列表 + 選用 SQLite sink。
   * - ``je_load_density.utils.generate_report``
     - HTML / JSON / XML / CSV / JUnit / Summary / Chart 產生器。
   * - ``je_load_density.utils.socket_server``
     - 長度框架 TCP 控制 plane,選用 TLS + token。
   * - ``je_load_density.utils.reliability``
     - 自適應重試、失敗預算、process supervisor、網路條件。
   * - ``je_load_density.utils.sla`` / ``regression``
     - SLA gate(latency / failure_rate / requests)+ 跨次 diff。
   * - ``je_load_density.utils.load_shapes``
     - Stages / Spike / Soak(包 Locust ``LoadTestShape``)。
   * - ``je_load_density.utils.throttle``
     - token-bucket 限流,跨 user 由 key 共享。
   * - ``je_load_density.utils.dashboard``
     - stdlib HTTP + SSE 即時進度 dashboard。
   * - ``je_load_density.utils.notifier``
     - Slack Block Kit + Teams MessageCard summary poster。
   * - ``je_load_density.utils.auth``
     - OAuth2 client(含 token cache)、JWT 簽發、AWS SigV4 簽章。
   * - ``je_load_density.utils.linter`` / ``schema``
     - Action JSON linter(5 條規則)+ JSON Schema 匯出器。
   * - ``je_load_density.utils.ci_annotations``
     - GitHub Actions ``::error::`` / ``::warning::`` 註解。
   * - ``je_load_density.utils.graphql``
     - 將 GraphQL query / variables 組成 POST task。
   * - ``je_load_density.wrapper.user_template``
     - 12 種 Locust user;``scenario_runner`` + ``request_executor``。
   * - ``je_load_density.wrapper.start_wrapper``
     - ``start_test`` 派發(``_USER_REGISTRY``)。
   * - ``je_load_density.wrapper.create_locust_env``
     - ``prepare_env`` / ``create_env``,以 local/master/worker 模式
       建立 Locust 環境(支援 ``load_shape``)。
   * - ``je_load_density.mcp_server``
     - 對外 13 個工具,讓 Claude 驅動 LoadDensity。
   * - ``je_load_density.action_lsp``
     - LSP server(completion + diagnostics)供編輯器整合。
   * - ``je_load_density.gui``
     - 選用 PySide6(表單 + 即時統計面板)。

逐步說明
--------

#. 呼叫端透過 CLI、MCP 工具、socket server,或直接呼叫
   ``execute_action(...)`` 送進一份動作 JSON。
#. ``Executor.execute_action`` 依 ``event_dict``(``LD_*`` + 安全
   builtins)派發每一步驟。
#. 當步驟為 ``LD_start_test``,派發器選擇 user template(12 種其一),
   依 ``variables`` / ``csv_sources`` / ``db_sources`` 填入參數解析器,
   並依 ``load_shape`` / ``shape_config`` 構造可選的 ``LoadTestShape``,
   再呼叫 ``prepare_env``。
#. ``prepare_env`` 以 local、master 或 worker 模式建立 Locust
   ``Environment`` 並啟動執行。
#. 每個 user 每 tick 執行 ``run_scenario``。對每個 ``execute_task``:
   throttle bucket → network conditioner → ``${...}`` 展開 → retry
   policy → 請求。
#. 回應後:assertions / extractors 執行,Locust 請求事件寫入
   ``test_record_instance`` 與 ``failure_budget``。
#. 報告、指標 exporter、SLA gate、即時 dashboard、Slack/Teams 通知與
   SQLite 持久化讀取累積的紀錄。
