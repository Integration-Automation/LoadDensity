# LoadDensity

<p align="center">
  <strong>多協定壓力與負載自動化框架：Locust + WebSocket + gRPC + MQTT + 原生 socket，搭配內建電池的 JSON 動作執行器。</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/je-load-density/"><img src="https://img.shields.io/pypi/v/je_load_density" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/je-load-density/"><img src="https://img.shields.io/pypi/pyversions/je_load_density" alt="Python Version"></a>
  <a href="https://github.com/Integration-Automation/LoadDensity/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Integration-Automation/LoadDensity" alt="License"></a>
  <a href="https://loaddensity.readthedocs.io/en/latest/"><img src="https://readthedocs.org/projects/loaddensity/badge/?version=latest" alt="Documentation Status"></a>
</p>

<p align="center">
  <a href="../README.md">English</a> |
  <a href="README_zh-CN.md">简体中文</a>
</p>

---

LoadDensity（`je_load_density`）從 Locust 封裝起家，逐步擴展為完整的多協定負載框架：HTTP、FastHttp、WebSocket、gRPC、MQTT 與原生 TCP/UDP 等使用者模板，皆透過同一個 JSON 驅動的動作執行器；另含資料參數化、情境流程、報告、可觀測性、分散式 runner、錄製、持久化儲存，以及讓 Claude 端對端驅動測試的 MCP 控制介面。每個 executor 指令以 `LD_*` 命名、使用單一派發點，因此一份動作 JSON 可同時混用協定、exporter 與報告。

> **選用相依、可選安裝** — 每個協定驅動與 exporter 都以 `pip install je_load_density[<extra>]` 提供。僅做 HTTP 壓測者執行期不受影響。

## 目次

- [亮點](#亮點)
- [安裝](#安裝)
- [架構](#架構)
- [Quick Start](#quick-start)
- [核心 API](#核心-api)
- [動作 Executor](#動作-executor)
- [使用者模板](#使用者模板)
- [參數解析器](#參數解析器)
- [情境模式](#情境模式)
- [斷言與擷取](#斷言與擷取)
- [報告](#報告)
- [可觀測性](#可觀測性)
- [分散式 Master / Worker](#分散式-master--worker)
- [HAR 錄製／重放](#har-錄製重放)
- [持久化紀錄（SQLite）](#持久化紀錄sqlite)
- [MCP Server（給 Claude）](#mcp-server給-claude)
- [硬化控制 Socket](#硬化控制-socket)
- [GUI](#gui)
- [CLI 用法](#cli-用法)
- [測試紀錄](#測試紀錄)
- [例外處理](#例外處理)
- [日誌](#日誌)
- [支援平台](#支援平台)
- [授權](#授權)

## 亮點

- **一個 executor，六種協定** — HTTP、FastHttp、WebSocket、gRPC、MQTT、原生 TCP/UDP，全部透過 `LD_start_test` 以 `user` 切換派發。
- **JSON 驅動** — 每支測試皆為動作 JSON 列表；可手寫、由 HAR 匯入產生、由 MCP 工具排程，或經控制 socket 傳送。
- **參數解析器** — `${var.x}`、`${env.X}`、`${csv.source.col}`、`${faker.method}`，以及內建 `${uuid()}`、`${now()}`、`${randint(min,max)}` 等 helper；可從回應擷取值，後續 task 再用。
- **情境流程** — 以 `sequence`（預設）／`weighted`／`conditional`（`run_if`、`skip_if`）宣告 task 流程，無需動到 Python。
- **六種報告格式** — HTML、JSON、XML、CSV、JUnit XML，以及百分位摘要 JSON（總計、失敗率、per-name p50/p90/p95/p99）。
- **三種 exporter** — Prometheus HTTP 端點、InfluxDB line-protocol UDP/HTTP sink、OpenTelemetry OTLP gRPC。
- **分散式 runner** — `runner_mode="master"` / `"worker"`，跨機壓測使用同一份 start_test API。
- **HAR 錄製／重放** — 將真實瀏覽流量轉成可執行動作 JSON，含 regex include/exclude 過濾。
- **持久化紀錄** — 選用 SQLite sink，含 run／record／metadata schema，便於跨次回歸檢查。
- **MCP server** — `python -m je_load_density.mcp_server` 對外開 11 個工具，讓 Claude 端對端驅動 LoadDensity。
- **硬化控制 socket** — Length-prefix framing、選用 TLS、共享密鑰 token（環境變數或參數），同時保留與 PyBreeze 等工具相容的 legacy 模式。
- **即時 GUI** — 選用的 PySide6 GUI 含即時統計面板（RPS、平均、p95、失敗），翻譯為英文、繁體中文、日文、韓文。
- **CLI 子指令** — `run` / `run-dir` / `run-str` / `init` / `serve`。舊式 `-e/-d/-c/--execute_str` 旗標保留以維持下游工具相容。

## 安裝

```bash
pip install je_load_density
```

引入 [Locust](https://locust.io/) 與 `defusedxml`，僅此而已。

### 選用 extras

| Extra | 加入 |
|-------|------|
| `gui` | PySide6 + qt-material（圖形介面） |
| `websocket` | `websocket-client`（WebSocket user 模板） |
| `grpc` | `grpcio` + `protobuf`（gRPC user 模板） |
| `mqtt` | `paho-mqtt`（MQTT user 模板） |
| `prometheus` | `prometheus-client`（Prometheus exporter） |
| `opentelemetry` | OpenTelemetry SDK + OTLP gRPC exporter |
| `metrics` | `prometheus` + `opentelemetry` 一次裝 |
| `faker` | `Faker`（驅動 `${faker.method}` 占位符） |
| `mcp` | `mcp` SDK（驅動 MCP server） |
| `all` | 上列全部 |

```bash
pip install "je_load_density[gui]"
pip install "je_load_density[mqtt,grpc,websocket]"
pip install "je_load_density[metrics]"
pip install "je_load_density[mcp]"
pip install "je_load_density[all]"
```

### 開發安裝

```bash
git clone https://github.com/Integration-Automation/LoadDensity.git
cd LoadDensity
pip install -e ".[all]"
pip install -r requirements.txt
```

## 架構

```
┌─────────────────────────────────────────────────────────────────┐
│ CLI / MCP / GUI / 控制 Socket                                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ 動作 JSON
┌──────────────────▼──────────────────────────────────────────────┐
│ 動作 Executor（LD_* 派發 + 安全 builtin）                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │ start_test
┌──────────────────▼──────────────────────────────────────────────┐
│ locust_wrapper_proxy（每協定 task store）                       │
└──────────────────┬──────────────────────────────────────────────┘
                   │
   ┌───────────────┴───────────────┬──────────────┬──────────────┐
   ▼                               ▼              ▼              ▼
HTTP / FastHttp  WebSocket  gRPC  MQTT  原生 TCP / UDP
   │                               │              │              │
   └───────────────┬───────────────┴──────────────┴──────────────┘
                   │ Locust 事件
   ┌───────────────┴───────────────┐
   ▼                               ▼
test_record_instance         Prometheus / InfluxDB / OTel
   │
   ├── HTML / JSON / XML / CSV / JUnit / Summary 報告
   └── SQLite 持久化（跨次比對）
```

依賴方向永遠是動作層 → Locust。

## Quick Start

### Python API

```python
from je_load_density import start_test

start_test(
    user_detail_dict={"user": "fast_http_user"},
    user_count=50, spawn_rate=10, test_time=30,
    variables={"base": "https://httpbin.org"},
    tasks=[
        {"method": "get",  "request_url": "${var.base}/get"},
        {"method": "post", "request_url": "${var.base}/post",
         "json": {"hello": "world"},
         "assertions": [{"type": "status_code", "value": 200}]},
    ],
)
```

### 動作 JSON

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

CLI 執行：

```bash
python -m je_load_density run smoke.json
```

## 核心 API

完整公開介面見 `je_load_density/__init__.py` 的 `__all__`。

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

## 動作 Executor

每個動作為列表：

```python
["command_name"]                        # 無參數
["command_name", {"key": "value"}]      # 關鍵字參數
["command_name", [arg1, arg2]]          # 位置參數
```

最上層為裸列表，或 `{"load_density": [...]}` 包裝。

### 內建 `LD_*` 指令

| 群組 | 指令 |
|------|------|
| 核心 | `LD_start_test`、`LD_execute_action`、`LD_execute_files`、`LD_add_package_to_executor`、`LD_start_socket_server` |
| 報告 | `LD_generate_html(_report)`、`LD_generate_json(_report)`、`LD_generate_xml(_report)`、`LD_generate_csv_report`、`LD_generate_junit_report`、`LD_generate_summary_report`、`LD_summary` |
| 持久化 | `LD_persist_records`、`LD_list_runs`、`LD_fetch_run_records`、`LD_clear_records` |
| 參數 | `LD_register_variable(s)`、`LD_register_csv_source(s)`、`LD_clear_resolver` |
| 錄製 | `LD_load_har`、`LD_har_to_tasks`、`LD_har_to_action_json` |
| 指標 | `LD_start/stop_prometheus_exporter`、`LD_start/stop_influxdb_sink`、`LD_start/stop_opentelemetry_exporter` |

安全的 Python builtin（`print`、`len`、`range` 等）也可使用；`eval`、`exec`、`compile`、`__import__`、`breakpoint`、`open`、`input` 已被明確封鎖。

### 自訂指令

```python
from je_load_density import add_command_to_executor

def slack_notify(message: str) -> None:
    ...

add_command_to_executor({"LD_slack_notify": slack_notify})
```

## 使用者模板

所有模板皆透過 `start_test` 的 `user_detail_dict={"user": "<key>"}` 註冊；HTTP / WebSocket / gRPC / MQTT / raw socket 共用相同 task 結構，僅協定相關欄位不同。

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

### WebSocket

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

`stub_path` 與 `request_path` 在 `importlib.import_module` 之前皆通過嚴格識別符 regex 驗證，traversal 攻擊將被拒絕。

### MQTT

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

僅用標準函式庫，無需安裝。

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

| 占位符 | 解析為 |
|--------|--------|
| `${var.NAME}` | `register_variable(s)` 設定的值 |
| `${env.NAME}` | 環境變數 `NAME` |
| `${csv.SOURCE.COL}` | CSV 來源 `SOURCE` 的下一筆（預設循環） |
| `${faker.METHOD}` | `Faker().METHOD()`（lazy import） |
| `${uuid()}` | 新 UUID 4 字串 |
| `${now()}` | 本地 ISO-8601 時間（秒） |
| `${randint(min, max)}` | 密碼學強度隨機整數 |

未知占位符原樣保留，便於 dry run 偵錯。

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
|------|------|
| `sequence` | 依序執行所有 task（預設） |
| `weighted` | 每 tick 依 `weight` 加權挑一個 |
| `conditional` | 以 `run_if` / `skip_if` 預測式控制 |

預測式：`bool`、`"${var.x}"`、`{"equals": [a,b]}`、`{"not_equals": [a,b]}`、`{"in": [needle, haystack]}`、`{"truthy": value}`。

## 斷言與擷取

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

斷言類型：`status_code`、`contains`、`not_contains`、`json_path`、`header`。
擷取來源：`json_path`、`header`、`status_code`。

## 報告

```python
from je_load_density import (
    generate_html_report, generate_json_report, generate_xml_report,
    generate_csv_report, generate_junit_report, generate_summary_report,
)

generate_html_report("report")           # report.html
generate_json_report("report")           # report_success.json + report_failure.json
generate_xml_report("report")            # report_success.xml  + report_failure.xml
generate_csv_report("report")            # report.csv
generate_junit_report("report-junit")    # report-junit.xml（CI）
generate_summary_report("report-sum")    # 總計 + per-name p50/p90/p95/p99
```

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
|------|------|
| Prometheus | `loaddensity_requests_total`、`loaddensity_request_latency_ms`、`loaddensity_response_bytes` |
| InfluxDB | `loaddensity_request` line-protocol（UDP 或 HTTP） |
| OTel | `loaddensity.requests`、`loaddensity.request.latency`、`loaddensity.response.size` |

三者皆 lazy load，由對應 install extra 控管相依。

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

Master 在開始 ramp 前最多等 60 秒，等待 `expected_workers` 個 worker 加入。

## HAR 錄製／重放

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

可吃 Chrome / Firefox DevTools、mitmproxy、Charles 等錄製。狀態碼會轉成 `status_code` 斷言。

## 持久化紀錄（SQLite）

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

Schema 採延遲建立。`run_id` 與 `name` 上有索引，跨次查詢快速。

## MCP Server（給 Claude）

```bash
pip install "je_load_density[mcp]"
python -m je_load_density.mcp_server
```

接到 Claude Desktop / Code：

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

對外開 11 個工具：`run_test`、`run_action_json`、`create_project`、`list_executor_commands`、`import_har`、`generate_reports`、`summary`、`persist_records`、`list_runs`、`fetch_run`、`clear_records`。

## 硬化控制 Socket

```bash
python -m je_load_density serve \
    --host 0.0.0.0 --port 9940 --framed \
    --token "$LOAD_DENSITY_SOCKET_TOKEN" \
    --tls-cert /etc/loaddensity/server.crt \
    --tls-key /etc/loaddensity/server.key
```

- 4-byte big-endian 長度前綴框架（1 MiB 上限）
- 選用 TLS（`ssl.create_default_context`，TLS 1.2+ minimum）
- 共享密鑰 token，以 `hmac.compare_digest` 比對；一旦設定，所有 payload 須使用 `{"token": "...", "command": [...]}` 信封，可以 `"op": "quit"` 停機
- Token 也可由 `LOAD_DENSITY_SOCKET_TOKEN` 環境變數讀取
- 保留未驗證 legacy 模式以維持相容

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

GUI 提供英文、繁體中文、日文、韓文翻譯，以及每秒輪詢 `test_record_instance` 的即時統計面板（RPS、平均、p95、失敗）。

## CLI 用法

```
python -m je_load_density run FILE              # 執行單一動作 JSON 檔
python -m je_load_density run-dir DIR           # 執行 DIR 下所有 .json
python -m je_load_density run-str JSON          # 執行 inline JSON
python -m je_load_density init PATH             # 建立專案骨架
python -m je_load_density serve [--host ...]    # 啟動控制 socket
```

舊式 `-e/-d/-c/--execute_str` 仍接受，相容下游工具。

## 測試紀錄

`test_record_instance.test_record_list` 與 `error_record_list` 收集每筆請求：`Method`、`test_url`、`name`、`status_code`、`response_time_ms`、`response_length`，失敗則含 `error`。報告與 SQLite sink 直接讀取此處。

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

所有自訂例外皆繼承 `LoadDensityTestException`；攔該類別即可全面處理。

## 日誌

LoadDensity 提供已配置好的 logger（`load_density_logger`，位於 `je_load_density.utils.logging.loggin_instance`）。以標準 `logging` 模組 API 即可整合既有日誌系統。

## 支援平台

| 平台 | 狀態 |
|------|------|
| Windows 10 / 11 | 完整支援 |
| macOS | 完整支援 |
| Ubuntu / Linux | 完整支援 |
| Raspberry Pi | 已測 3B+ 以上 |

需 Python 3.10+。

## 授權

MIT — 見 [LICENSE](../LICENSE)。
