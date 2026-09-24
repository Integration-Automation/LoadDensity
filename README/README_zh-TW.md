# LoadDensity

<p align="center">
  <strong>多協定壓力與負載自動化框架:Locust + WebSocket + gRPC + MQTT + 原生 socket,搭配內建電池的 JSON 動作執行器。</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/je-load-density/"><img src="https://img.shields.io/pypi/v/je_load_density" alt="PyPI 版本"></a>
  <a href="https://pypi.org/project/je-load-density/"><img src="https://img.shields.io/pypi/pyversions/je_load_density" alt="Python 版本"></a>
  <a href="https://github.com/Integration-Automation/LoadDensity/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Integration-Automation/LoadDensity" alt="授權"></a>
  <a href="https://loaddensity.readthedocs.io/en/latest/"><img src="https://readthedocs.org/projects/loaddensity/badge/?version=latest" alt="文件"></a>
</p>

<p align="center">
  <a href="../README.md">English</a> |
  <a href="README_zh-CN.md">简体中文</a>
</p>

---

LoadDensity(`je_load_density`)從 Locust 封裝起家,逐步成長為完整的多協定負載框架:HTTP、FastHttp、WebSocket、gRPC、MQTT,以及原生 TCP/UDP 使用者模板,全部收攏在同一個 JSON 驅動的動作執行器之後;另外還有參數化資料、情境流程、報告、可觀測性、分散式 runner、錄製、持久化儲存,以及讓 Claude 端對端驅動負載測試的 MCP 控制介面等模組。每個 executor 指令都有確定性的名稱(`LD_*`)與單一派發點,因此一份動作 JSON 可以在同一個腳本裡混用協定、exporter 與報告。

> **選用相依、選擇性安裝** — 每個協定驅動與 exporter 都以 `pip install je_load_density[<extra>]` 這個 extra 提供。對只需要 HTTP 負載測試的使用者而言,基礎安裝的體積維持不變。

## 目次

- [亮點](#亮點)
- [安裝](#安裝)
- [架構](#架構)
  - [系統總覽](#系統總覽)
  - [動作生命週期](#動作生命週期)
  - [User 派發](#user-派發)
  - [模組地圖](#模組地圖)
- [Quick Start](#quick-start)
- [食譜 (Recipes)](#食譜-recipes)
- [核心 API](#核心-api)
- [動作 Executor](#動作-executor)
- [使用者模板](#使用者模板)
  - [HTTP / FastHttp](#http--fasthttp)
  - [WebSocket](#websocket)
  - [gRPC](#grpc)
  - [MQTT](#mqtt)
  - [原生 TCP / UDP](#原生-tcp--udp)
- [參數解析器](#參數解析器)
- [情境模式](#情境模式)
- [斷言與擷取](#斷言與擷取)
- [報告](#報告)
- [可觀測性](#可觀測性)
- [分散式 Master / Worker](#分散式-master--worker)
- [HAR 錄製/重放](#har-錄製重放)
- [持久化紀錄(SQLite)](#持久化紀錄sqlite)
- [MCP Server(給 Claude)](#mcp-server給-claude)
- [硬化控制 Socket](#硬化控制-socket)
- [SLA Gate 與跨次回歸 Diff](#sla-gate-與跨次回歸-diff)
- [Load Shapes](#load-shapes)
- [Think Time 與 Throttle](#think-time-與-throttle)
- [匯入器](#匯入器)
- [Action JSON Linter / Schema / LSP](#action-json-linter--schema--lsp)
- [GitHub Actions 註解](#github-actions-註解)
- [可靠度](#可靠度)
- [即時 Dashboard](#即時-dashboard)
- [Slack / Teams / StatsD](#slack--teams--statsd)
- [Auth](#auth)
- [k6 / JMeter 匯入器](#k6--jmeter-匯入器)
- [GitHub Action 與 pre-commit](#github-action-與-pre-commit)
- [VS Code 擴充套件](#vs-code-擴充套件)
- [範例與本地實驗環境](#範例與本地實驗環境)
- [GUI](#gui)
- [CLI 用法](#cli-用法)
- [測試紀錄](#測試紀錄)
- [例外處理](#例外處理)
- [日誌](#日誌)
- [支援平台](#支援平台)
- [更多模組](#更多模組)
- [授權](#授權)

## 亮點

- **一個 executor,41 種 user type。** HTTP、FastHttp、**Async HTTP/2 (httpx)**、HTTP/3、WebSocket、SSE、gRPC(unary 與 server/client/bidi 串流)、MQTT、原生 TCP/UDP、SQL(SQLAlchemy)、Redis、Kafka、**MongoDB**,以及更多協定(AMQP、NATS、Pulsar、Cassandra、Elasticsearch、Modbus、OPC-UA、LDAP、SNMP、SMTP/IMAP、FTP/SFTP 等)— 全部透過同一個 `LD_start_test` 指令,以 `user_detail_dict["user"]` 這個 key 派發。
- **動作 JSON 即契約。** 每個指令都經由 `Executor.event_dict` 解析;不論是手寫、由 HAR 匯入產生、透過控制 socket 傳送,還是由 MCP 工具驅動,動作列表都是同一套。
- **參數解析器處處可用。** `${var.NAME}`、`${env.NAME}`、`${csv.SOURCE.COL}`、`${db.SOURCE.COL}`、`${faker.method}`,以及內建的 `${uuid()}`、`${now()}`、`${randint(min,max)}` 輔助函式;從某個回應擷取的值,可以餵給下一個 task 的 URL、header、body 或斷言。
- **無需 Python 的情境流程。** 把 task 宣告成 `sequence`(預設)、`weighted` 或帶 `run_if` / `skip_if` 判斷式的 `conditional`;per-task 的 `think_time`、`throttle.rps` 與 `retry`(`{transient, flaky, permanent}` 預算)不必寫等待迴圈就能控制節奏與韌性。
- **內建 load shapes。** `load_shape="stages"|"spike"|"soak"` 搭配 JSON `shape_config` — 不需要 Locust subclass。
- **生產等級的可靠度。** 自適應重試(指數退避 + 抖動 + 每種錯誤類別各自的預算)、滑動視窗失敗預算 / circuit breaker、帶硬性逾時 watchdog 的 process supervisor、in-process 網路條件模擬(latency / jitter / loss)。
- **SLA gate + 回歸 diff。** 當 latency / failure-rate / request-count 規則破線時,`LD_assert_sla` 會讓 CI 失敗;`LD_diff_runs` 比對兩個持久化到 SQLite 的 run,並標出超過容忍範圍的 per-name 回歸。
- **七種報告格式。** HTML、JSON、XML、CSV、JUnit XML、百分位摘要 JSON,再加上選用的 matplotlib **chart 報告**(透過 `[charts]` extra 產生 `latency-over-time` 與 `RPS-over-time` PNG)。
- **四種即時 exporter。** Prometheus HTTP 端點、InfluxDB line-protocol UDP/HTTP sink、OpenTelemetry OTLP gRPC exporter、**Datadog DogStatsD UDP** sink — 全部延遲匯入,並由對應的安裝 extra 控制。
- **即時 web dashboard。** `start_dashboard()` 會啟動一個 stdlib HTTP + SSE 伺服器,把執行中的 RPS / avg / p95 / failure 計數串流到任意瀏覽器,並附上 per-name 表格。
- **Slack + Teams 通知。** 以 build_summary 的輸出為基礎的 Block Kit + MessageCard 摘要張貼器(`LD_post_slack_summary`、`LD_post_teams_summary`)。
- **斷言 + 擷取。** `status_code`、`contains`、`not_contains`、`json_path`、`header` 斷言在 Locust 的 `catch_response` 下執行;來源為 `json_path` / `header` / `status_code` 的擷取器會把值寫回參數解析器。
- **分散式 runner。** `runner_mode="master"` / `"worker"` 以同一套 `start_test` API 進行跨機負載;master 會先等待設定的 worker 數量最多 60 秒,再開始 ramp。
- **六種匯入器。** HAR(瀏覽器流量)、Postman v2.1 collection、OpenAPI 3.x spec、獨立的 cURL 指令、**k6 腳本**,以及 **JMeter JMX** plan — 每一種都能轉成動作 JSON 或一個可直接餵給 `LD_start_test` 的 task。
- **Auth 輔助工具。** stdlib OAuth2 client(`client_credentials` / `password` / `refresh`,含 token cache)、JWT 簽章器(HS256/384/512 + RS256/384/512)、AWS SigV4 請求簽章器,再加上每個 HTTP 使用者模板都能透過 `task["cert"]` 支援 mTLS client-cert。
- **持久化紀錄。** 選用的 SQLite sink,採 `runs` / `records` / `metadata` schema 並建立索引以利跨次回歸檢查;開箱即可對空檔運作。
- **MCP server。** `python -m je_load_density.mcp_server` 對外開放 13 個工具,讓 Claude(Desktop、Code、任何 MCP client)不必離開對話就能執行測試、管理專案並取回報告。
- **動作 JSON 工具鏈。** 內建 linter(`LD_lint_action`)、JSON Schema 匯出器(`LD_export_schema`)、GitHub Actions 註解發送器(`LD_emit_github_annotations`)、stdlib LSP server(`python -m je_load_density.action_lsp`)、composite **GitHub Action** 包裝(`action.yml`)、**pre-commit hook**,以及 **VS Code 擴充套件** 骨架 — 編輯器 + CI 整合端對端到位。
- **硬化控制 socket。** 4-byte big-endian 長度前綴 framing(上限 1 MiB)、透過 `ssl.create_default_context` 的選用 TLS、以環境變數或參數提供的共享密鑰 token,再加上一個與 PyBreeze 等下游工具相容的 legacy 模式。
- **安全 executor。** 動作 JSON 檔只能呼叫 `LD_*` 指令,以及一份 22 個名稱的內建白名單(`print`、`len`、`sorted`、`sum` 等),此外別無其他。名單外的一切 — `eval`、`exec`、`compile`、`__import__`、`open`、`input`,以及 `getattr` / `setattr` / `vars` / `globals` 這些屬性與作用域內建 — 根本沒有註冊,因此無法被派發。
- **即時 GUI。** 選用的 PySide6 前端,附帶即時統計面板(RPS / avg / p95 / failures),已翻譯為英文、繁體中文、日文與韓文。
- **CLI 子指令。** `run` / `run-dir` / `run-str` / `init` / `bench` / `shell` / `serve`。舊式單旗標形式(`-e/-d/-c/--execute_str`)仍為下游工具保留。
- **跨平台。** Windows 10/11、macOS、Ubuntu/Linux、Raspberry Pi(3B+ 以上),Python 3.10+。

## 安裝

**穩定版:**

```bash
pip install je_load_density
```

引入 [Locust](https://locust.io/) 與 `defusedxml`,別無其他。

### 選用 extras

只安裝你會用到的切片:

| Extra | 加入 |
|-------|------|
| `gui` | PySide6 + qt-material(圖形前端) |
| `websocket` | `websocket-client`(WebSocket 使用者模板) |
| `grpc` | `grpcio` + `protobuf`(gRPC 使用者模板) |
| `mqtt` | `paho-mqtt`(MQTT 使用者模板) |
| `redis` | `redis`(Redis 使用者模板) |
| `kafka` | `kafka-python`(Kafka 使用者模板) |
| `sql` | `sqlalchemy`(SQL 使用者模板 + `${db.*}` 占位符) |
| `mongo` | `pymongo`(MongoDB 使用者模板) |
| `http2` | `httpx[http2]`(Async HTTP/2 使用者模板) |
| `auth` | `cryptography`(RS256/384/512 JWT 簽章) |
| `reliability` | `psutil`(ProcessSupervisor) |
| `prometheus` | `prometheus-client`(Prometheus exporter) |
| `opentelemetry` | OpenTelemetry SDK + OTLP gRPC exporter |
| `metrics` | `prometheus` + `opentelemetry` 一次裝齊 |
| `charts` | `matplotlib`(圖表渲染報告) |
| `yaml` | `pyyaml`(OpenAPI YAML 載入) |
| `faker` | `Faker`(驅動 `${faker.method}` 占位符) |
| `all` | 上列全部 |

```bash
pip install "je_load_density[gui]"
pip install "je_load_density[mqtt,grpc,websocket]"
pip install "je_load_density[metrics]"
pip install "je_load_density[all]"
```

### 開發安裝

```bash
git clone https://github.com/Integration-Automation/LoadDensity.git
cd LoadDensity
pip install -e ".[all]"
pip install -r requirements.txt
```

硬性需求:Python **3.10+**、`locust`、`defusedxml`。

## 架構

### 系統總覽

```mermaid
flowchart LR
  subgraph Authoring
    A1["Action JSON files"]
    A2["Programmatic start_test"]
    A3["HAR → action JSON"]
    A4["MCP / Claude"]
  end

  subgraph Core
    EXE["Action Executor<br/>event_dict (LD_*)"]
    RES["Parameter Resolver<br/>${var} / ${env} / ${csv} / ${faker}"]
    REC["test_record_instance"]
  end

  subgraph Runners
    LOC["Locust local"]
    MAS["Locust master"]
    WRK["Locust worker"]
  end

  subgraph Templates
    HTTP["HTTP / FastHttp"]
    WS["WebSocket"]
    GRPC["gRPC"]
    MQTT["MQTT"]
    SOCK["Raw TCP/UDP"]
  end

  subgraph Outputs
    REP["Reports<br/>HTML/JSON/XML/CSV/JUnit/Summary"]
    EXP["Exporters<br/>Prometheus · InfluxDB · OTel"]
    SQL["SQLite persistence"]
  end

  A1 --> EXE
  A2 --> EXE
  A3 --> A1
  A4 --> EXE
  EXE --> RES
  EXE --> LOC
  EXE --> MAS
  EXE --> WRK
  LOC --> HTTP & WS & GRPC & MQTT & SOCK
  MAS --> WRK
  WRK --> HTTP & WS & GRPC & MQTT & SOCK
  HTTP & WS & GRPC & MQTT & SOCK --> REC
  REC --> REP
  REC --> EXP
  REC --> SQL
```

### 動作生命週期

```mermaid
flowchart LR
  IN["Action<br/>[cmd, args_or_kwargs]"] --> DISP["event_dict[cmd]"]
  DISP -- "LD_start_test" --> SEED["Seed resolver from<br/>variables / csv_sources"]
  SEED --> PICK["Pick user template<br/>(_USER_REGISTRY)"]
  PICK --> ENV["prepare_env<br/>(local / master / worker)"]
  ENV --> RUN["Locust runner ticks"]
  RUN --> EXPAND["Parameter resolver<br/>expands ${...} per task"]
  EXPAND --> EXEC["execute_task<br/>(per-protocol request)"]
  EXEC -- response --> ASSERT["assertions + extractors"]
  ASSERT --> EVT["Locust request event"]
  EVT --> REC["test_record_instance.append"]
  DISP -- "LD_generate_*_report" --> RREAD["Read from test_record_instance"]
  RREAD --> OUT["Report file(s)"]
```

### User 派發

```mermaid
flowchart TB
  CMD["start_test(user_detail_dict={...})"] --> KEY{"user key?"}
  KEY -- "fast_http_user (default)" --> FH["FastHttpUserWrapper<br/>(geventhttpclient)"]
  KEY -- "http_user" --> H["HttpUserWrapper<br/>(requests)"]
  KEY -- "websocket_user" --> WS["WebSocketUserWrapper<br/>(websocket-client)"]
  KEY -- "grpc_user" --> G["GrpcUserWrapper<br/>(grpcio + importlib lookup)"]
  KEY -- "mqtt_user" --> M["MqttUserWrapper<br/>(paho-mqtt)"]
  KEY -- "socket_user" --> S["SocketUserWrapper<br/>(stdlib TCP / UDP)"]
  FH & H & WS & G & M & S --> SC["scenario_runner<br/>(sequence / weighted / conditional)"]
  SC --> RX["request_executor.execute_task"]
```

### 模組地圖

```
je_load_density/
├── __init__.py                       # Public API re-exports
├── __main__.py                       # CLI: run / run-dir / run-str / init / serve
├── gui/                              # Optional PySide6 front-end
│   ├── language_wrapper/             # En / zh-TW / Ja / Ko translations
│   ├── load_density_gui_thread.py    # Worker thread for non-blocking starts
│   ├── log_to_ui_filter.py           # Forward logger records to the UI pane
│   ├── main_widget.py                # Form-based test configurator
│   ├── main_window.py                # PySide6 main window shell
│   └── stats_panel.py                # Live RPS / avg / p95 / failures panel
├── mcp_server/                       # MCP server (13 tools for Claude)
│   ├── __main__.py
│   └── server.py
├── utils/
│   ├── callback/                     # callback_executor (post-action callbacks)
│   ├── exception/                    # LoadDensity* exception hierarchy + tags
│   ├── executor/                     # Executor class · event_dict · safe builtins
│   ├── file_process/                 # Directory walker · project scaffolder
│   ├── generate_report/              # HTML / JSON / XML / CSV / JUnit / Summary
│   ├── get_data_structure/           # API data helper (legacy)
│   ├── json/                         # JSON read/write · placeholder normaliser
│   ├── logging/                      # Configured load_density_logger
│   ├── metrics/                      # Prometheus · InfluxDB · OpenTelemetry sinks
│   ├── package_manager/              # Dynamic package loader (LD_add_package_*)
│   ├── parameterization/             # ParameterResolver + CSV / faker sources
│   ├── project/                      # Project template + create_project_dir
│   ├── recording/                    # HAR → action JSON converter
│   ├── socket_server/                # Length-framed TCP control plane (+TLS+token)
│   ├── test_record/                  # In-memory record list + SQLite persistence
│   └── xml/                          # defusedxml-backed XML helpers
└── wrapper/
    ├── create_locust_env/            # prepare_env / create_env (local/master/worker)
    ├── event/                        # request_hook (binds Locust events → records)
    ├── proxy/                        # Per-protocol task store (locust_wrapper_proxy)
    │   └── user/                     # fast_http / http / websocket / grpc / mqtt / socket
    ├── start_wrapper/                # start_test dispatcher (_USER_REGISTRY)
    └── user_template/                # Locust user classes + scenario_runner + request_executor
load_density_driver/                  # Standalone driver builds
test/                                 # pytest test suite
docs/                                 # Sphinx documentation (En / Zh / API)
```

## Quick Start

### 以 Python 跑 HTTP 負載測試

```python
from je_load_density import start_test

start_test(
    user_detail_dict={"user": "fast_http_user"},
    user_count=50,
    spawn_rate=10,
    test_time=30,
    variables={"base": "https://httpbin.org"},
    tasks=[
        {"method": "get",  "request_url": "${var.base}/get"},
        {"method": "post", "request_url": "${var.base}/post",
         "json": {"hello": "world"},
         "assertions": [{"type": "status_code", "value": 200}]},
    ],
)
```

### Action JSON

```json
{"load_density": [
  ["LD_register_variables", {"variables": {"base": "https://httpbin.org"}}],
  ["LD_start_test", {
    "user_detail_dict": {"user": "fast_http_user"},
    "user_count": 20, "spawn_rate": 10, "test_time": 30,
    "tasks": [
      {"method": "get",  "request_url": "${var.base}/get"},
      {"method": "post", "request_url": "${var.base}/post",
       "json": {"hello": "world"}}
    ]
  }],
  ["LD_generate_summary_report", {"report_name": "smoke"}]
]}
```

由 CLI 執行:

```bash
python -m je_load_density run smoke.json
```

### Action 形式

```python
["command"]                                    # no args
["command", {"key": "value"}]                  # kwargs
["command", [arg1, arg2]]                      # positional
```

最外層文件可以是一個純 list,或一個 `{"load_density": [...]}` wrapper。

## 食譜 (Recipes)

涵蓋最常見需求的簡短複製貼上片段。每一則都能以 Python 的 `start_test` 呼叫,或以 `LD_start_test` 動作執行。

| 食譜 | 展示 |
|---|---|
| **HTTP smoke** | `fast_http_user` + `status_code` 斷言 + summary 報告。 |
| **登入流程** | 從登入回應 `extract` token,後續受保護的呼叫透過 `${var.auth}` header 重用。 |
| **加權混合** | `mode: "weighted"` 配合每個 task 的 `weight`,把流量偏向熱門端點。 |
| **WebSocket echo** | `websocket_user` 的 `connect → sendrecv → close`,搭配 `expect` 子字串斷言。 |
| **gRPC unary** | `grpc_user` 配 `stub_path` / `request_path` + metadata tuple list + 每次呼叫的 timeout。 |
| **MQTT pub/sub** | `mqtt_user` 的 `connect → subscribe → publish → disconnect`,對本地 broker。 |
| **原生 TCP/UDP** | `socket_user` 帶 `payload`(文字或 `hex:…`)與 `expect_substring`。 |
| **分散式跑法** | 一個 `runner_mode="master"` + N 個 `runner_mode="worker"` 行程,對同一份動作 JSON。 |
| **HAR replay** | `LD_load_har` → `LD_har_to_action_json`,含 regex include / exclude。 |
| **匯出指標** | `LD_start_prometheus_exporter`、`LD_start_influxdb_sink`、`LD_start_opentelemetry_exporter`。 |
| **持久化結果** | `LD_persist_records` 帶 `label` + `metadata` 存進 SQLite,再以 `LD_list_runs` 看趨勢。 |
| **MCP 驅動** | 把 Claude 接到 `python -m je_load_density.mcp_server`,呼叫 `run_test` / `generate_reports`。 |
| **SLA gate** | `LD_assert_sla` 以 `latency_p95` / `failure_rate` 規則在回歸時讓 CI 失敗。 |
| **Spike shape** | `load_shape="spike"` + `shape_config`,驅動 baseline → spike → baseline 的 ramp。 |
| **Think time + throttle** | `task["think_time"]` 與 `task["throttle"]={"rps":...}` 控制流量節奏。 |
| **Postman / OpenAPI / cURL** | `LD_postman_to_action_json` / `LD_openapi_to_action_json` / `LD_curl_to_task` 一次性匯入。 |
| **Redis / Kafka / SQL** | 使用 `user_detail_dict={"user": "redis_user"}` 等,搭配協定專屬的 task 欄位。 |

把這張表和專屬章節(見目次)對照,就能看到完整的參數面。

## 核心 API

```python
from je_load_density import (
    start_test, prepare_env, create_env,
    execute_action, execute_files, executor, add_command_to_executor,
    test_record_instance, locust_wrapper_proxy,
    register_variable, register_variables,
    register_csv_source, register_csv_sources,
    parameter_resolver, resolve,
    har_to_action_json, har_to_tasks, load_har,
    persist_records, list_runs, fetch_run_records,
    start_prometheus_exporter, stop_prometheus_exporter,
    start_influxdb_sink, stop_influxdb_sink,
    start_opentelemetry_exporter, stop_opentelemetry_exporter,
    start_load_density_socket_server,
    generate_html_report, generate_json_report, generate_xml_report,
    generate_csv_report, generate_junit_report, generate_summary_report,
    build_summary,
    create_project_dir, callback_executor, read_action_json,
)
```

完整的公開介面定義於 `je_load_density/__init__.py` 的 `__all__`。

## 動作 Executor

動作 executor 把字串指令名稱對應到一個 Python callable。每個後端、exporter 與報告 helper 都註冊在 `event_dict` 之下。

### 內建 `LD_*` 指令

| 類別 | 指令 |
|-------|----------|
| 核心 | `LD_start_test`、`LD_execute_action`、`LD_execute_files`、`LD_add_package_to_executor`、`LD_start_socket_server` |
| 報告 | `LD_generate_html(_report)`、`LD_generate_json(_report)`、`LD_generate_xml(_report)`、`LD_generate_csv_report`、`LD_generate_junit_report`、`LD_generate_summary_report`、`LD_generate_chart_report`、`LD_summary` |
| 持久化 | `LD_persist_records`、`LD_list_runs`、`LD_fetch_run_records`、`LD_clear_records` |
| 參數 | `LD_register_variable(s)`、`LD_register_csv_source(s)`、`LD_register_db_source(s)`、`LD_clear_resolver` |
| 錄製 | `LD_load_har`、`LD_har_to_*`、`LD_postman_to_*`、`LD_openapi_to_*`、`LD_curl_to_task`、`LD_k6_script_to_*`、`LD_jmeter_to_*` |
| 指標 | `LD_start/stop_prometheus_exporter`、`LD_start/stop_influxdb_sink`、`LD_start/stop_opentelemetry_exporter`、`LD_start/stop_statsd_sink` |
| 品質 / DX | `LD_lint_action`、`LD_lint_action_file`、`LD_export_schema`、`LD_emit_github_annotations` |
| SLA / 回歸 | `LD_evaluate_sla`、`LD_assert_sla`、`LD_diff_runs` |
| 可靠度 | `LD_install_failure_budget`、`LD_uninstall_failure_budget`、`LD_install_network_conditioner`、`LD_uninstall_network_conditioner` |
| Dashboard / 通知 | `LD_start_dashboard`、`LD_stop_dashboard`、`LD_post_slack_summary`、`LD_post_teams_summary` |

安全的 Python 內建(`print`、`len`、`range` 等)也可接受;`eval`、`exec`、`compile`、`__import__`、`breakpoint`、`open`、`input` 則被明確封鎖。

### 自訂指令

```python
from je_load_density import add_command_to_executor

def slack_notify(message: str) -> None:
    ...

add_command_to_executor({"LD_slack_notify": slack_notify})
```

## 使用者模板

每個模板都透過 `user_detail_dict={"user": "<key>"}` 註冊在 `start_test` 之下。task 在 HTTP、WebSocket、gRPC、MQTT 與原生 socket 使用者之間共用相同的形狀;只有協定專屬的欄位不同。

### HTTP / FastHttp

```python
start_test(
    user_detail_dict={"user": "fast_http_user"},
    user_count=50, spawn_rate=10, test_time=60,
    variables={"base": "https://api.example.com"},
    tasks=[
        {"method": "post", "request_url": "${var.base}/login",
         "json": {"email": "u@example.com", "password": "secret"},
         "extract": [{"var": "auth", "from": "json_path", "path": "data.token"}]},
        {"method": "get", "request_url": "${var.base}/profile",
         "headers": {"Authorization": "Bearer ${var.auth}"},
         "assertions": [{"type": "status_code", "value": 200}]},
    ],
)
```

`fast_http_user` 是預設值;當第三方轉接器需要時,`http_user` 會把 client 換成 `requests` 風格的同步呼叫。

### WebSocket

`pip install "je_load_density[websocket]"`

```python
start_test(
    user_detail_dict={"user": "websocket_user"},
    user_count=10, spawn_rate=5, test_time=60,
    tasks=[
        {"method": "connect", "request_url": "wss://echo.example.com/socket"},
        {"method": "sendrecv", "payload": '{"ping": 1}', "expect": "pong"},
        {"method": "close"},
    ],
)
```

### gRPC

`pip install "je_load_density[grpc]"`

```python
start_test(
    user_detail_dict={"user": "grpc_user"},
    user_count=20, spawn_rate=5, test_time=60,
    tasks=[{
        "name": "say_hello",
        "target": "localhost:50051",
        "stub_path": "pkg.greeter_pb2_grpc.GreeterStub",
        "request_path": "pkg.greeter_pb2.HelloRequest",
        "method": "SayHello",
        "payload": {"name": "world"},
        "metadata": [["x-token", "abc"]],
        "timeout": 5,
    }],
)
```

`stub_path` 與 `request_path` 會在 `importlib.import_module` 之前先以嚴格的識別字 regex 驗證,因此 traversal 式攻擊會被拒絕。

### MQTT

`pip install "je_load_density[mqtt]"`

```python
start_test(
    user_detail_dict={"user": "mqtt_user"},
    user_count=10, spawn_rate=5, test_time=60,
    tasks=[
        {"method": "connect",   "broker": "127.0.0.1:1883"},
        {"method": "subscribe", "topic":  "telemetry/in", "qos": 1},
        {"method": "publish",   "topic":  "telemetry/out", "payload": "ping", "qos": 1},
        {"method": "disconnect"},
    ],
)
```

### 原生 TCP / UDP

只用 stdlib;無需安裝。

```python
start_test(
    user_detail_dict={"user": "socket_user"},
    user_count=20, spawn_rate=5, test_time=60,
    tasks=[
        {"protocol": "tcp", "target": "127.0.0.1:9000",
         "payload": "PING\n", "expect_bytes": 64,
         "expect_substring": "PONG"},
        {"protocol": "udp", "target": "127.0.0.1:9000",
         "payload": "hex:DEADBEEF", "expect_bytes": 4},
    ],
)
```

## 參數解析器

占位符會在每個 task 上自動展開:

| 占位符 | 解析為 |
|-------------|-------------|
| `${var.NAME}` | 傳給 `register_variable(s)` 的值 |
| `${env.NAME}` | 環境變數 `NAME` |
| `${csv.SOURCE.COL}` | CSV 源 `SOURCE` 的下一列(預設循環) |
| `${faker.METHOD}` | `Faker().METHOD()`(延遲匯入) |
| `${uuid()}` | 新的 UUID 4 字串 |
| `${now()}` | 本地 ISO-8601 時間戳(秒) |
| `${randint(min, max)}` | 加密強度的隨機整數 |

```python
from je_load_density import register_variable, register_csv_source

register_variable("base", "https://api.example.com")
register_csv_source("users", "users.csv")
```

或從動作 JSON:

```json
["LD_register_variables", {"variables": {"base": "https://api.example.com"}}]
["LD_register_csv_sources", {"sources": [{"name": "users", "file_path": "users.csv"}]}]
```

未知的占位符會原樣保留,因此 dry run 時缺少的資料會顯而易見。

## 情境模式

```json
{
  "mode": "weighted",
  "tasks": [
    {"method": "get", "request_url": "/products", "weight": 3},
    {"method": "get", "request_url": "/expensive", "weight": 1}
  ]
}
```

| 模式 | 行為 |
|------|-----------|
| `sequence` | 每個 tick 依序執行每個 task(預設) |
| `weighted` | 每個 tick 依 `weight` 挑一個 task |
| `conditional` | 使用對參數解析器求值的 `run_if` / `skip_if` 判斷式 |

判斷式:`bool`、`"${var.x}"`、`{"equals": [a,b]}`、`{"not_equals": [a,b]}`、`{"in": [needle, haystack]}`、`{"truthy": value}`。

## 斷言與擷取

兩者都在 Locust 的 `catch_response` 下執行;失敗的斷言會在每份報告中浮現。

```json
{
  "method": "post",
  "request_url": "${var.base}/login",
  "json": {"email": "u@example.com", "password": "secret"},
  "assertions": [
    {"type": "status_code", "value": 200},
    {"type": "json_path", "path": "data.role", "value": "admin"}
  ],
  "extract": [
    {"var": "auth_token", "from": "json_path", "path": "data.token"},
    {"var": "request_id", "from": "header",    "name": "X-Request-Id"}
  ]
}
```

斷言類型:`status_code`、`contains`、`not_contains`、`json_path`、`header`。擷取來源:`json_path`、`header`、`status_code`。

## 報告

六種格式,皆從 `test_record_instance` 取用:

```python
from je_load_density import (
    generate_html_report, generate_json_report, generate_xml_report,
    generate_csv_report, generate_junit_report, generate_summary_report,
)

generate_html_report("report")           # report.html
generate_json_report("report")           # report_success.json + report_failure.json
generate_xml_report("report")            # report_success.xml  + report_failure.xml
generate_csv_report("report")            # report.csv
generate_junit_report("report-junit")    # report-junit.xml (CI)
generate_summary_report("report-sum")    # totals + per-name p50/p90/p95/p99
```

| 格式 | 輸出形狀 | Spec 驅動? |
|--------|--------------|--------------|
| HTML | `<base>.html`(成功 + 失敗表格,色彩標記) | single |
| JSON | `<base>_success.json` + `<base>_failure.json` | split |
| XML | `<base>_success.xml` + `<base>_failure.xml` | split |
| CSV | `<base>.csv` | single |
| JUnit | `<base>-junit.xml`(CI 原生) | single |
| Summary | `<base>.json`(per-name p50/p90/p95/p99) | single |

## 可觀測性

```python
from je_load_density import (
    start_prometheus_exporter, start_influxdb_sink, start_opentelemetry_exporter,
)

start_prometheus_exporter(port=9646, addr="127.0.0.1")
start_influxdb_sink(transport="udp", host="influxdb", port=8089)
start_opentelemetry_exporter(endpoint="http://otel-collector:4317",
                             service_name="loaddensity")
```

| Sink | 指標 |
|------|---------|
| Prometheus | `loaddensity_requests_total`、`loaddensity_request_latency_ms`、`loaddensity_response_bytes` |
| InfluxDB | `loaddensity_request` line-protocol points(UDP 或 HTTP) |
| OTel | `loaddensity.requests`、`loaddensity.request.latency`、`loaddensity.response.size` |

三者都延遲載入,並由對應的安裝 extra 控制。

## 分散式 Master / Worker

```python
# master
start_test(
    user_detail_dict={"user": "fast_http_user"},
    runner_mode="master",
    master_bind_host="0.0.0.0", master_bind_port=5557,
    expected_workers=4,
    web_ui_dict={"host": "0.0.0.0", "port": 8089},
    user_count=400, spawn_rate=40, test_time=600,
    tasks=[...],
)

# worker
start_test(
    user_detail_dict={"user": "fast_http_user"},
    runner_mode="worker",
    master_host="10.0.0.10", master_port=5557,
    tasks=[...],
)
```

master 會等待最多 60 秒,讓 `expected_workers` 個 worker 完成註冊,再開始負載 ramp。

## HAR 錄製/重放

```python
from je_load_density import load_har, har_to_action_json

har = load_har("recording.har")
action_json = har_to_action_json(
    har,
    user="fast_http_user",
    user_count=20, spawn_rate=10, test_time=120,
    include=[r"api\.example\.com"],
    exclude=[r"\.svg$"],
)
```

來自 Chrome / Firefox DevTools、mitmproxy、Charles 等的擷取全都可用。狀態碼會化為每個產生 task 上的 `status_code` 斷言。

## 持久化紀錄(SQLite)

```python
from je_load_density import persist_records, list_runs, fetch_run_records

run_id = persist_records(
    "loadtests.db",
    label="checkout-2026-04-28",
    metadata={"branch": "dev", "commit": "abc1234"},
)
for row in list_runs("loadtests.db", limit=10):
    print(row)
```

Schema 會延遲建立;空檔也沒問題。`run_id` 與 `name` 上的索引讓跨次查詢保持快速。

## MCP Server(給 Claude)

```bash
pip install je_load_density
python -m je_load_density.mcp_server
```

server 自己在 stdio 上講 MCP(JSON-RPC 2.0,一行一則訊息),因此不需要 `mcp` SDK;`[mcp]` extra 是空的,只是保留下來讓舊的安裝指令仍能運作。

把它接進 Claude Desktop / Code:

```json
{
  "mcpServers": {
    "loaddensity": {
      "command": "python",
      "args": ["-m", "je_load_density.mcp_server"]
    }
  }
}
```

對外開放十三個工具:`run_test`、`run_action_json`、`create_project`、`list_executor_commands`、`import_har`、`generate_reports`、`summary`、`persist_records`、`list_runs`、`fetch_run`、`clear_records`、`generate_from_openapi`、`generate_from_curls`。

每個工具接收的路徑(`create_project` 的 `path`、`import_har` 的 `file_path`、run 工具的 `database_path`、`generate_from_openapi` 的 `openapi_path`,以及 `generate_reports` 的 `base_name`)都必須解析在 server 的 root 之內。root 預設為工作目錄,除非 `JE_LOAD_DENSITY_MCP_ROOT` 指向他處。root 以外的路徑會被拒絕,因此被所讀內容操縱的模型無法在他處讀寫檔案。

## 硬化控制 Socket

```bash
python -m je_load_density serve \
    --host 0.0.0.0 --port 9940 --framed \
    --token "$LOAD_DENSITY_SOCKET_TOKEN" \
    --tls-cert /etc/loaddensity/server.crt \
    --tls-key /etc/loaddensity/server.key
```

- 4-byte big-endian 長度前綴 frame(上限 1 MiB)
- 選用 TLS(磁碟上的 cert/key;`ssl.create_default_context`,最低 TLS 1.2+)
- 以 `hmac.compare_digest` 比對的共享密鑰 token;一旦設定,所有 payload 都必須使用 `{"token": "...", "command": [...]}`,並可設 `"op": "quit"` 來停止 server
- token 也會從 `LOAD_DENSITY_SOCKET_TOKEN` 環境變數讀取
- 保留 legacy 未驗證模式以維持向後相容

## GUI

```bash
pip install "je_load_density[gui]"
```

```python
import sys
from PySide6.QtWidgets import QApplication
from je_load_density.gui.main_window import LoadDensityUI

app = QApplication(sys.argv)
window = LoadDensityUI()
window.show()
sys.exit(app.exec())
```

GUI 內附英文、繁體中文、日文與韓文翻譯,以及一個每秒輪詢 `test_record_instance` 一次的即時統計面板(RPS、平均 / p95 latency、失敗計數)。

## CLI 用法

```
python -m je_load_density run FILE              # execute one action JSON file
python -m je_load_density run-dir DIR           # execute every .json in DIR
python -m je_load_density run-str JSON          # execute an inline JSON string
python -m je_load_density init PATH             # scaffold a project skeleton
python -m je_load_density bench URL [--users N] # quick asyncio HTTP benchmark (no Locust)
python -m je_load_density shell                 # interactive REPL with ld pre-imported
python -m je_load_density serve [--host ...]    # start the control socket
```

舊式單旗標形式(`-e/-d/-c/--execute_str`)仍為與下游工具向後相容而接受。

## 測試紀錄

`test_record_instance.test_record_list` 與 `error_record_list` 蒐集每次請求,內含 `Method`、`test_url`、`name`、`status_code`、`response_time_ms`、`response_length`、`start_time`(epoch 秒,因此報告可跨兩份 list 還原請求順序),失敗時還帶 `error`。報告與 SQLite sink 直接從這些 list 讀取。

## 例外處理

```
LoadDensityTestException
├── LoadDensityTestJsonException
├── LoadDensityGenerateJsonReportException
├── LoadDensityTestExecuteException
├── LoadDensityAssertException
├── LoadDensityHTMLException
├── LoadDensityAddCommandException
├── XMLException → XMLTypeException
└── CallbackExecutorException
```

所有自訂例外都繼承自 `LoadDensityTestException`;捕捉這一個類別即可涵蓋公開介面。

## 日誌

LoadDensity 對外提供單一已設定的 logger(`load_density_logger`),位於 `je_load_density.utils.logging.loggin_instance`。以標準的 `logging` 模組 API 把它接進你既有的日誌基礎設施。

它把 WARNING+ 寫到 stderr,INFO+ 寫到 `~/.je_load_density/logs/LoadDensity.log`(設 `LOAD_DENSITY_LOG_FILE` 可寫到別處,或設為 `os.devnull` 關閉檔案)。檔案在第一筆紀錄時才開啟,因此匯入套件不會在工作目錄寫入任何東西;它由每個行程共享並附加,每一行都帶著行程 id。

## 支援平台

| 平台 | 狀態 |
|----------|--------|
| Windows 10 / 11 | 完整支援 |
| macOS | 完整支援 |
| Ubuntu / Linux | 完整支援 |
| Raspberry Pi | 已在 3B+ 以上測試 |

需要 Python 3.10+。

## SLA Gate 與跨次回歸 Diff

```python
from je_load_density import assert_sla, build_summary, diff_runs

assert_sla([
    {"type": "failure_rate", "value": 0.02},
    {"type": "latency_p95", "value": 800},
    {"type": "latency_p95", "name": "/checkout", "value": 500},
    {"type": "requests", "op": "gte", "value": 1000},
], summary=build_summary())

report = diff_runs("loadtests.db",
                   baseline_run_id=42, current_run_id=43,
                   tolerance=0.10)
if report["has_regressions"]:
    raise SystemExit(report["regressions"])
```

支援的規則類型:`latency_p50` / `_p90` / `_p95` / `_p99`、
`latency_mean`、`failure_rate`、`requests`。`op` 為 `lt`(預設
`lte`)、`gt`、`gte`。per-endpoint 規則傳入 `name`。

## Load Shapes

```python
start_test(
    user_detail_dict={"user": "fast_http_user"},
    load_shape="spike",
    shape_config={"baseline_users": 20, "spike_users": 200,
                  "spawn_rate": 50, "pre_seconds": 30,
                  "spike_seconds": 30, "post_seconds": 30},
    tasks=[...],
)
```

內建:`"stages"`(`{duration, users, spawn_rate}` 的 list)、
`"spike"`、`"soak"`。全部在背後回傳 Locust `LoadTestShape`
子類別。

## Think Time 與 Throttle

```json
[
  {"method": "get", "request_url": "${var.base}/home",
   "think_time": {"min": 0.5, "max": 1.5}},
  {"method": "get", "request_url": "${var.base}/checkout",
   "throttle": {"key": "checkout", "rps": 25, "burst": 5}}
]
```

兩種控制都是 per-task,並在請求發出前解析。
Throttle bucket 由 `key` 在使用者之間共享。

## 匯入器

```python
from je_load_density import (
    load_har, har_to_action_json,
    load_postman_collection, postman_to_action_json,
    load_openapi, openapi_to_action_json,
    curl_to_task,
)

action_a = har_to_action_json(load_har("recording.har"))
action_b = postman_to_action_json(load_postman_collection("collection.json"))
action_c = openapi_to_action_json(load_openapi("openapi.yaml"))
task     = curl_to_task("curl -X POST https://api/login -d '{\"x\":1}'")
```

OpenAPI 會把 `{param}` 路徑段替換成 `${var.param}`,讓
呼叫端能透過 `register_variables` 提供值。

## Action JSON Linter / Schema / LSP

```python
from je_load_density import lint_action, export_schema

findings = lint_action({"load_density": [["LD_typo"]]})
# [{'rule': 'unknown-command', 'severity': 'error', ...}]

export_schema("docs/reference/loaddensity-action-schema.json")
```

供編輯器整合的 stdlib LSP:

```bash
python -m je_load_density.action_lsp   # or: loaddensity-lsp
```

`textDocument/completion` 回傳每個 `LD_*` 指令;
`publishDiagnostics` 在每次變更時執行 linter。

## GitHub Actions 註解

```python
from je_load_density import emit_github_annotations

emit_github_annotations(title="LoadDensity")
# ::error title=LoadDensity::GET /checkout (HTTP 500): timeout
```

每筆失敗紀錄一行 `::error::`;reviewer 會在
PR 的 *Files Changed* 檢視中直接看到它們。

## 範例與本地實驗環境

* [`examples/`](examples/) 提供 12 個可執行的 recipe(smoke、auth flow、
  weighted mix、WebSocket、MQTT、Redis、spike shape、SLA gate、HAR /
  Postman / OpenAPI 匯入)。
* [`docker/`](docker/) 以一個 `docker compose up -d` 帶起 httpbin、Mosquitto(MQTT)、Redis、
  Kafka 與 Prometheus。

## 可靠度

```python
from je_load_density import (
    AdaptiveRetryPolicy, run_with_retry,
    install_failure_budget, install_network_conditioner,
    with_watchdog,
)

# Adaptive retry — exponential backoff + jitter + per-error-class budget
policy = AdaptiveRetryPolicy(transient_budget=5, flaky_budget=2,
                              base_delay=0.1, max_delay=2.0)
run_with_retry(lambda: do_request(), policy=policy)

# Per-task retry (declarative)
# task["retry"] = {"transient": 3, "flaky": 1, "base_delay": 0.2}

# Failure budget — abort the run when 5% of the last 30s fail
install_failure_budget(threshold=0.05, window_seconds=30,
                       runner_quit_callback=lambda: env.runner.quit())

# Network conditioner — inject latency / jitter / loss
install_network_conditioner(latency_ms=50, jitter_ms=20, loss_rate=0.01,
                             name_filter="/checkout")

# Watchdog — hard-kill a hung CI run
with_watchdog(lambda: execute_action(action_json), timeout_seconds=600)
```

## 即時 Dashboard

```python
from je_load_density import start_dashboard

start_dashboard(host="127.0.0.1", port=8765, refresh_seconds=1.0)
# open http://127.0.0.1:8765 → /events streams JSON snapshots via SSE
```

## Slack / Teams / StatsD

```python
from je_load_density import (
    post_slack_summary, post_teams_summary, start_statsd_sink,
)

start_statsd_sink(host="dogstatsd", port=8125, prefix="loaddensity")
post_slack_summary("https://hooks.slack.com/services/...")
post_teams_summary("https://outlook.office.com/webhook/...")
```

## Auth

```python
from je_load_density import (
    OAuth2Client, sign_jwt, sign_aws_request,
)

client = OAuth2Client("https://idp/token", "id", "secret", scope="read:x")
token = client.get_client_credentials()  # cached for the lifetime of expires_in

jwt = sign_jwt({"sub": "alice"}, secret="topsecret",
                algorithm="HS256", expires_in_seconds=300)

aws_headers = sign_aws_request(
    method="GET",
    url="https://s3.amazonaws.com/mybucket/key",
    region="us-east-1", service="s3",
    access_key="AK", secret_key="sk",
)
```

mTLS:

```json
{"method": "get", "request_url": "https://mtls.api/x",
 "cert": ["/etc/ssl/client.pem", "/etc/ssl/key.pem"]}
```

## k6 / JMeter 匯入器

```python
from je_load_density import (
    load_k6_script, k6_script_to_action_json,
    load_jmeter_jmx, jmeter_to_action_json,
)

action = k6_script_to_action_json(load_k6_script("script.js"))
action = jmeter_to_action_json(load_jmeter_jmx("plan.jmx"))
```

結合既有的 HAR / Postman / OpenAPI / cURL 匯入器,
LoadDensity 能從每一種常見的負載測試來源格式讀取。

## GitHub Action 與 pre-commit

```yaml
# .github/workflows/load.yml
- uses: ./   # or: Integration-Automation/LoadDensity@v1
  with:
    action-file: actions/smoke.json
    extras: "metrics,websocket"
    fail-on-error: "true"
```

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Integration-Automation/LoadDensity
  rev: v1.0.0
  hooks:
    - id: loaddensity-lint
```

## VS Code 擴充套件

`editors/vscode/` 提供一個最小的擴充套件,以 stdio 啟動
`python -m je_load_density.action_lsp` 取得 completion +
diagnostics。以 `npm install && npm run package` 建置,再安裝
產生的 `.vsix`。`.github/workflows/editors.yml` 這個 workflow 會在 `editors/` 下每次變更時
打包它、檢查 Chrome 擴充套件並建置 JetBrains plugin。

## 更多模組

於 2026-05 擴充加入。每一個都延遲匯入,且只需要它自己的 extra。

- **Asyncio 引擎。** `je_load_density.engine.asyncio_engine.run_async_load` 不透過 Locust,直接以 asyncio 驅動一個 HTTP 目標,並寫出與 Locust 使用者相同的紀錄,4xx/5xx 一律計為失敗。`bench` 子指令包裝了它:

  ```bash
  python -m je_load_density bench https://api.example.com/health --users 10 --duration 10
  ```

  選項:`--method`、`--body`、`--http2`、`--max-in-flight`。
- **Cloud workers**(`aws`、`gcp`、`azure` 或 `cloud` extras):`cloud.aws_fargate.launch_fargate_workers`、`cloud.aws_lambda.invoke_lambda_workers`(以 `lambda_worker_handler` 作為函式進入點)、`cloud.azure_aci.launch_aci_workers` 與 `cloud.gcp_cloud_run.run_cloud_run_job` 為分散式跑法啟動遠端 worker。
- **Chaos 輔助工具**:`utils.chaos.toxiproxy` 在 Toxiproxy 執行個體上新增與移除 latency 或 bandwidth toxic(`install_latency`、`install_bandwidth`、`reset_all`);`utils.chaos.chaos_mesh` 建構並套用 Chaos Mesh manifest(`build_network_delay`、`apply_manifest`、`delete_manifest`)。
- **Stub server**:`utils.stub_server.start_stub_server` / `stop_stub_server` 供應罐頭回應,讓情境能對一個假後端執行。它從一個執行緒供應,可與 Locust 的 gevent 使用者並存;對 asyncio 引擎則要在獨立行程啟動它,因為引擎自己行程裡的伺服器執行緒永遠得不到排程。
- **更多報告格式**,在上述七種之外:Allure、cost、CycloneDX、Excel、latency histogram、PDF(`pdf` extra)、SARIF 與一張 service map,各自對應 `utils/generate_report/` 下一個 `generate_*_report.py` 模組。
- **部署範本** 位於 `deploy/`:一份 Helm chart、一個 Kubernetes operator(`k8s` extra)、Terraform、一張 Grafana dashboard 與 CI 範本。

## 授權

MIT — 詳見 [LICENSE](../LICENSE)。

Copyright (c) 2022~2026 JE-Chen
