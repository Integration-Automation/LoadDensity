Architecture
============

Overview
--------

LoadDensity is a thin facade over Locust that adds a JSON-driven action
executor, a multi-protocol user template registry, scenario flow, data
parameterisation, observability sinks, production-grade reliability
controls (adaptive retry, failure budget, network conditioner), live
web dashboard, Slack/Teams notifiers, OAuth2/JWT/SigV4 auth helpers,
and an MCP control surface.

The dependency direction always points from the action layer down to
Locust, never the other way around — your action JSON defines what to
do, the executor maps each command to a Python callable, and Locust
runs the resulting load.

System overview
---------------

.. mermaid::

    flowchart LR
      subgraph Authoring
        A1["Action JSON files"]
        A2["Programmatic start_test"]
        A3["HAR / Postman / OpenAPI /<br/>cURL / k6 / JMeter imports"]
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
        GRPC["gRPC (unary + streaming)"]
        MQ["MQTT / Kafka"]
        SOCK["Raw TCP / UDP"]
        DATA["SQL / Redis / MongoDB"]
      end

      subgraph Outputs
        REP["Reports<br/>HTML/JSON/XML/CSV/JUnit/Summary/Chart"]
        EXP["Exporters<br/>Prometheus · InfluxDB · OTel · StatsD"]
        DASH["Live Dashboard (SSE)"]
        NOT["Notifiers<br/>Slack · Teams"]
        SQL["SQLite persistence + cross-run diff"]
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

Action lifecycle
----------------

.. mermaid::

    flowchart LR
      IN["Action<br/>[cmd, args_or_kwargs]"] --> DISP["event_dict[cmd]"]
      DISP -- "LD_start_test" --> SEED["Seed resolver from<br/>variables / csv / db sources"]
      SEED --> PICK["Pick user template<br/>(_USER_REGISTRY)"]
      PICK --> ENV["prepare_env<br/>(local / master / worker · load_shape)"]
      ENV --> RUN["Locust runner ticks"]
      RUN --> THR["throttle.rps cap"]
      THR --> COND["network conditioner<br/>(latency / jitter / loss)"]
      COND --> EXPAND["Parameter resolver<br/>expands ${...} per task"]
      EXPAND --> RETRY["per-task retry policy<br/>(transient / flaky / permanent)"]
      RETRY --> EXEC["execute_task<br/>(per-protocol request)"]
      EXEC -- response --> ASSERT["assertions + extractors"]
      ASSERT --> EVT["Locust request event"]
      EVT --> REC["test_record_instance.append"]
      EVT --> FB["failure_budget · trip on breach"]

User dispatch
-------------

.. mermaid::

    flowchart TB
      CMD["start_test(user_detail_dict={...})"] --> KEY{"user key?"}
      KEY -- "fast_http_user (default)" --> FH["FastHttpUserWrapper"]
      KEY -- "http_user" --> H["HttpUserWrapper (requests)"]
      KEY -- "async_http_user" --> AH["AsyncHttpUserWrapper<br/>(httpx, HTTP/2 optional)"]
      KEY -- "websocket_user" --> WS["WebSocketUserWrapper"]
      KEY -- "sse_user" --> SS["SseUserWrapper"]
      KEY -- "grpc_user" --> G["GrpcUserWrapper<br/>(unary + streaming)"]
      KEY -- "mqtt_user" --> M["MqttUserWrapper"]
      KEY -- "kafka_user" --> K["KafkaUserWrapper"]
      KEY -- "socket_user" --> S["SocketUserWrapper"]
      KEY -- "sql_user" --> SQ["SqlUserWrapper"]
      KEY -- "redis_user" --> R["RedisUserWrapper"]
      KEY -- "mongo_user" --> MO["MongoUserWrapper"]
      FH & H & AH & WS & SS & G & M & K & S & SQ & R & MO --> SC["scenario_runner<br/>(sequence / weighted / conditional)"]
      SC --> RX["request_executor.execute_task"]

Module map
----------

.. code-block:: text

    je_load_density/
    ├── __init__.py                       # Public API re-exports (108 symbols)
    ├── __main__.py                       # CLI: run / run-dir / run-str / init / serve
    ├── action_lsp/                       # LSP server for action JSON
    ├── mcp_server/                       # MCP server (11 tools for Claude)
    ├── tools/                            # CLI helpers (pre-commit linter, …)
    ├── gui/                              # Optional PySide6 front-end
    ├── utils/
    │   ├── auth/                         # OAuth2 / JWT / AWS SigV4
    │   ├── callback/                     # callback_executor
    │   ├── ci_annotations/               # GitHub Actions annotation emitter
    │   ├── dashboard/                    # Live web dashboard (SSE)
    │   ├── exception/                    # LoadDensity* exception hierarchy
    │   ├── executor/                     # Executor · event_dict · safe builtins
    │   ├── file_process/                 # Directory walker · project scaffolder
    │   ├── generate_report/              # HTML / JSON / XML / CSV / JUnit / Summary / Chart
    │   ├── graphql/                      # GraphQL helper
    │   ├── json/                         # JSON I/O
    │   ├── linter/                       # Action JSON linter
    │   ├── load_shapes/                  # Stages / Spike / Soak
    │   ├── logging/                      # Configured load_density_logger
    │   ├── metrics/                      # Prometheus · InfluxDB · OTel · DogStatsD
    │   ├── notifier/                     # Slack · Teams
    │   ├── package_manager/              # Dynamic package loader
    │   ├── parameterization/             # var / env / csv / db / faker resolver
    │   ├── project/                      # Project template
    │   ├── recording/                    # HAR / Postman / OpenAPI / cURL / k6 / JMeter
    │   ├── regression/                   # Cross-run diff
    │   ├── reliability/                  # adaptive_retry / failure_budget /
    │   │                                 # network_conditioner / process_supervisor
    │   ├── schema/                       # Action JSON Schema export
    │   ├── sla/                          # SLA gate
    │   ├── socket_server/                # Length-framed TCP plane (+TLS+token)
    │   ├── test_record/                  # In-memory records + SQLite persistence
    │   ├── throttle/                     # Shared token-bucket
    │   └── xml/                          # defusedxml helpers
    └── wrapper/
        ├── create_locust_env/            # prepare_env / create_env (local/master/worker + shape)
        ├── event/                        # request_hook (Locust events → records)
        ├── proxy/                        # Per-protocol task store (12 users)
        └── user_template/                # 12 Locust users + scenario_runner + request_executor
    load_density_driver/                  # Standalone driver builds
    examples/                             # 12 runnable recipes
    docker/                               # Local lab (httpbin / mosquitto / redis / kafka / prometheus)
    editors/vscode/                       # VS Code extension skeleton
    action.yml                            # Composite GitHub Action
    .pre-commit-hooks.yaml                # pre-commit entry
    test/                                 # pytest suite (225 tests)
    docs/                                 # Sphinx documentation (En / Zh / API)

Module responsibilities
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module
     - Purpose
   * - ``je_load_density.utils.executor``
     - ``Executor`` class, dispatch table (``LD_*``), safe-builtin gate.
   * - ``je_load_density.utils.parameterization``
     - ``ParameterResolver`` for ``${var/env/csv/db/faker}`` + built-ins.
   * - ``je_load_density.utils.recording``
     - HAR / Postman / OpenAPI / cURL / k6 / JMeter importers.
   * - ``je_load_density.utils.metrics``
     - Prometheus exporter, InfluxDB sink, OTel exporter, DogStatsD sink.
   * - ``je_load_density.utils.test_record``
     - In-memory record list + optional SQLite sink.
   * - ``je_load_density.utils.generate_report``
     - HTML / JSON / XML / CSV / JUnit / summary / chart generators.
   * - ``je_load_density.utils.socket_server``
     - Length-framed TCP control plane with optional TLS and token.
   * - ``je_load_density.utils.reliability``
     - Adaptive retry, failure budget, process supervisor, network conditioner.
   * - ``je_load_density.utils.sla`` / ``regression``
     - SLA gate (latency / failure_rate / requests rules) and cross-run diff.
   * - ``je_load_density.utils.load_shapes``
     - Stages / Spike / Soak load shapes (wrap Locust ``LoadTestShape``).
   * - ``je_load_density.utils.throttle``
     - Token-bucket throttle shared across users by key.
   * - ``je_load_density.utils.dashboard``
     - stdlib HTTP + SSE live progress dashboard.
   * - ``je_load_density.utils.notifier``
     - Slack Block Kit + Teams MessageCard summary posters.
   * - ``je_load_density.utils.auth``
     - OAuth2 client (with token cache), JWT signer, AWS SigV4 signer.
   * - ``je_load_density.utils.linter`` / ``schema``
     - Action JSON linter (5 rules) + JSON Schema exporter.
   * - ``je_load_density.utils.ci_annotations``
     - GitHub Actions ``::error::`` / ``::warning::`` emitter.
   * - ``je_load_density.utils.graphql``
     - GraphQL helper that composes a POST task with query / variables.
   * - ``je_load_density.wrapper.user_template``
     - 12 Locust user classes; ``scenario_runner`` + ``request_executor``.
   * - ``je_load_density.wrapper.start_wrapper``
     - ``start_test`` dispatcher (``_USER_REGISTRY``).
   * - ``je_load_density.wrapper.create_locust_env``
     - ``prepare_env`` / ``create_env`` building a Locust environment in
       local, master, or worker mode (with optional ``load_shape``).
   * - ``je_load_density.mcp_server``
     - MCP server exposing 11 tools so Claude can drive LoadDensity.
   * - ``je_load_density.action_lsp``
     - LSP server (completion + diagnostics) for editor integration.
   * - ``je_load_density.gui``
     - Optional PySide6 widgets (form controls + live stats panel).

Action lifecycle, step by step
------------------------------

#. Caller submits an action JSON via the CLI, MCP tool, socket server,
   or direct ``execute_action(...)`` call.
#. ``Executor.execute_action`` dispatches each step against
   ``event_dict`` (``LD_*`` commands plus safe builtins).
#. When the step is ``LD_start_test``, the dispatcher selects a user
   template (one of 12), seeds the parameter resolver from any
   ``variables`` / ``csv_sources`` / ``db_sources``, optionally
   constructs a ``LoadTestShape`` from ``load_shape`` /
   ``shape_config``, then calls ``prepare_env``.
#. ``prepare_env`` builds a Locust ``Environment`` in local, master,
   or worker mode and starts the run.
#. Each user runs ``run_scenario`` (or the protocol equivalent) per
   tick. Before each ``execute_task``: throttle bucket → network
   conditioner → ``${...}`` expansion → retry policy → request.
#. After the response: assertions / extractors fire, a Locust request
   event feeds ``test_record_instance`` and ``failure_budget``.
#. Reports, metrics exporters, SLA gates, live dashboard, Slack/Teams
   notifiers, and SQLite persistence consume the accumulated records.
