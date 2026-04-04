# LoadDensity

[![Python](https://img.shields.io/pypi/pyversions/je_load_density)](https://pypi.org/project/je_load_density/)
[![PyPI](https://img.shields.io/pypi/v/je_load_density)](https://pypi.org/project/je_load_density/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://readthedocs.org/projects/loaddensity/badge/?version=latest)](https://loaddensity.readthedocs.io/en/latest/)

**LoadDensity** 是一個基於 [Locust](https://locust.io/) 建構的高效能負載與壓力測試自動化框架。它對 Locust 的核心功能進行了簡化封裝，提供快速使用者生成、透過模板與 JSON 腳本進行彈性測試配置、多格式報告生成（HTML / JSON / XML）、內建 GUI 圖形介面、透過 TCP Socket 伺服器進行遠端執行，以及測試後工作流程的回呼機制。

**[English](../README.md)** | **[简体中文](README_zh-CN.md)**

---

## 功能特色

- **簡化的 Locust 封裝** — 將 Locust 的 `Environment`、`Runner` 和 `User` 類別抽象化為簡潔的高階 API。
- **兩種使用者類型** — 同時支援 `HttpUser` 和 `FastHttpUser`（基於 geventhttpclient，吞吐量更高）。
- **快速使用者生成** — 可配置生成速率，輕鬆擴展至數千名並行使用者。
- **JSON 驅動的測試腳本** — 將測試場景定義為 JSON 檔案，無需撰寫 Python 程式碼即可執行。
- **動作執行器** — 內建的事件驅動執行器，將動作名稱映射到函式。支援批次執行與檔案驅動執行。
- **報告生成** — 匯出三種格式的測試結果：
  - **HTML** — 包含成功/失敗記錄的樣式化表格
  - **JSON** — 適合程式化處理的結構化資料
  - **XML** — 標準 XML 輸出，適合 CI/CD 整合
- **請求鉤子** — 自動記錄每個請求（成功與失敗），包含方法、URL、狀態碼、回應內容、標頭與錯誤資訊。
- **回呼執行器** — 將觸發函式與回呼函式串聯，用於測試後工作流程（例如：執行測試後自動生成報告）。
- **TCP Socket 伺服器** — 基於 gevent 的遠端執行伺服器。透過 TCP 接收 JSON 指令以遠端執行測試。
- **專案腳手架** — 自動生成專案目錄結構，包含關鍵字模板與執行器腳本。
- **套件管理器** — 在執行期間動態載入外部 Python 套件，並將其函式註冊到執行器中。
- **GUI 圖形介面（選用）** — 基於 PySide6 的圖形介面，支援即時日誌顯示，提供英文與繁體中文介面。
- **CLI 命令列支援** — 直接從命令列執行測試、運行腳本或建立專案結構。
- **跨平台** — 支援 Windows、macOS 和 Linux。

## 安裝

### 基本安裝（CLI 與函式庫）

```bash
pip install je_load_density
```

### 包含 GUI 支援

```bash
pip install je_load_density[gui]
```

這會安裝 [PySide6](https://doc.qt.io/qtforpython/) 和 [qt-material](https://github.com/UN-GCPDS/qt-material) 以提供圖形介面。

## 系統需求

- Python **3.10** 或更高版本
- [Locust](https://locust.io/)（會作為依賴項自動安裝）

## 快速上手

### 1. 使用 Python API

```python
from je_load_density import start_test

# 定義使用者配置與任務
result = start_test(
    user_detail_dict={"user": "fast_http_user"},
    user_count=50,
    spawn_rate=10,
    test_time=10,
    tasks={
        "get": {"request_url": "http://httpbin.org/get"},
        "post": {"request_url": "http://httpbin.org/post"},
    }
)
```

**參數說明：**
| 參數 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `user_detail_dict` | `dict` | — | 使用者類型配置。`{"user": "fast_http_user"}` 或 `{"user": "http_user"}` |
| `user_count` | `int` | `50` | 模擬使用者總數 |
| `spawn_rate` | `int` | `10` | 每秒生成的使用者數量 |
| `test_time` | `int` | `60` | 測試持續時間（秒）。設為 `None` 則無限執行 |
| `web_ui_dict` | `dict` | `None` | 啟用 Locust Web UI，例如 `{"host": "127.0.0.1", "port": 8089}` |
| `tasks` | `dict` | — | HTTP 方法對應請求 URL 的映射 |

### 2. 使用 JSON 腳本檔案

建立 JSON 檔案（`test_scenario.json`）：

```json
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
```

從 Python 執行：

```python
from je_load_density import execute_action, read_action_json

execute_action(read_action_json("test_scenario.json"))
```

### 3. 使用 CLI 命令列

```bash
# 執行單一 JSON 腳本檔案
python -m je_load_density -e test_scenario.json

# 執行目錄中所有 JSON 檔案
python -m je_load_density -d ./test_scripts/

# 執行內嵌 JSON 字串
python -m je_load_density --execute_str '[["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}, "user_count": 10, "spawn_rate": 5, "test_time": 5, "tasks": {"get": {"request_url": "http://httpbin.org/get"}}}]]'

# 使用模板建立新專案
python -m je_load_density -c MyProject
```

### 4. 使用 GUI 圖形介面

```python
from je_load_density.gui.main_window import LoadDensityUI
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = LoadDensityUI()
window.show()
sys.exit(app.exec())
```

## 報告生成

執行測試後，從記錄的資料生成報告：

```python
from je_load_density import (
    generate_html_report,
    generate_json_report,
    generate_xml_report,
)

# HTML 報告 — 建立 "my_report.html"
generate_html_report("my_report")

# JSON 報告 — 建立 "my_report_success.json" 和 "my_report_failure.json"
generate_json_report("my_report")

# XML 報告 — 建立 "my_report_success.xml" 和 "my_report_failure.xml"
generate_xml_report("my_report")
```

## 進階用法

### 動作執行器

執行器將字串動作名稱映射到可呼叫的函式。所有 Python 內建函式也可使用。

```python
from je_load_density import executor, add_command_to_executor

# 註冊自訂函式
def my_custom_action(message):
    print(f"自訂動作: {message}")

add_command_to_executor({"my_action": my_custom_action})

# 程式化執行動作
executor.execute_action([
    ["my_action", ["Hello World"]],
    ["print", ["測試完成"]],
])
```

**內建執行器動作：**
| 動作名稱 | 說明 |
|---|---|
| `LD_start_test` | 啟動負載測試 |
| `LD_generate_html` | 生成 HTML 片段 |
| `LD_generate_html_report` | 生成完整 HTML 報告檔案 |
| `LD_generate_json` | 生成 JSON 資料結構 |
| `LD_generate_json_report` | 生成 JSON 報告檔案 |
| `LD_generate_xml` | 生成 XML 字串 |
| `LD_generate_xml_report` | 生成 XML 報告檔案 |
| `LD_execute_action` | 執行動作列表 |
| `LD_execute_files` | 從多個檔案執行動作 |
| `LD_add_package_to_executor` | 動態載入套件到執行器 |

### 回呼執行器

將觸發函式與回呼串聯：

```python
from je_load_density import callback_executor

def after_test():
    print("測試完成，正在生成報告...")

callback_executor.callback_function(
    trigger_function_name="user_test",
    callback_function=after_test,
    user_detail_dict={"user": "fast_http_user"},
    user_count=10,
    spawn_rate=5,
    test_time=5,
    tasks={"get": {"request_url": "http://httpbin.org/get"}},
)
```

### TCP Socket 伺服器（遠端執行）

啟動接收 JSON 指令的 TCP 伺服器：

```python
from je_load_density import start_load_density_socket_server

# 啟動伺服器（阻塞式）
start_load_density_socket_server(host="localhost", port=9940)
```

從客戶端發送指令：

```python
import socket, json

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 9940))

command = json.dumps([
    ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "user_count": 10, "spawn_rate": 5, "test_time": 5,
        "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
    }]
])
sock.send(command.encode("utf-8"))
response = sock.recv(8192)
print(response.decode("utf-8"))
sock.close()
```

發送 `"quit_server"` 可優雅地關閉伺服器。

### 專案腳手架

生成包含關鍵字模板與執行器腳本的專案：

```python
from je_load_density import create_project_dir

create_project_dir(project_path="./my_tests", parent_name="LoadDensity")
```

這會建立以下結構：
```
my_tests/
└── LoadDensity/
    ├── keyword/
    │   ├── keyword1.json    # FastHttpUser 測試模板
    │   └── keyword2.json    # HttpUser 測試模板
    └── executor/
        ├── executor_one_file.py   # 執行單一關鍵字檔案
        └── executor_folder.py     # 執行 keyword/ 目錄中所有檔案
```

### 動態套件載入

載入外部套件並將其函式註冊到執行器中：

```python
from je_load_density import executor

# 載入套件並使其函式可作為執行器動作使用
executor.execute_action([
    ["LD_add_package_to_executor", ["my_custom_package"]]
])
```

### 測試記錄

以程式化方式存取原始測試記錄：

```python
from je_load_density import test_record_instance

# 執行測試後
for record in test_record_instance.test_record_list:
    print(record["Method"], record["test_url"], record["status_code"])

for error in test_record_instance.error_record_list:
    print(error["Method"], error["test_url"], error["error"])

# 清除記錄
test_record_instance.clear_records()
```

## 架構

```
je_load_density/
├── __init__.py              # 公開 API 匯出
├── __main__.py              # CLI 進入點
├── gui/                     # PySide6 GUI（選用依賴）
│   ├── main_window.py       # 主視窗（QMainWindow）
│   ├── main_widget.py       # 測試參數表單與日誌面板
│   ├── load_density_gui_thread.py  # 測試背景執行緒
│   ├── log_to_ui_filter.py  # GUI 顯示的日誌攔截器
│   └── language_wrapper/    # 國際化（英文、繁體中文）
├── wrapper/
│   ├── create_locust_env/   # Locust Environment 與 Runner 設定
│   ├── start_wrapper/       # 高階 start_test() 進入點
│   ├── user_template/       # HttpUser 與 FastHttpUser 封裝
│   ├── proxy/               # 使用者代理容器與配置
│   └── event/               # 請求鉤子（記錄所有請求）
└── utils/
    ├── executor/            # 動作執行器（事件驅動）
    ├── generate_report/     # HTML、JSON、XML 報告生成器
    ├── test_record/         # 測試記錄儲存
    ├── socket_server/       # 遠端執行 TCP 伺服器
    ├── callback/            # 回呼函式執行器
    ├── project/             # 專案腳手架與模板
    ├── package_manager/     # 動態套件載入
    ├── json/                # JSON 檔案讀寫工具
    ├── xml/                 # XML 結構工具
    ├── file_process/        # 目錄檔案列表
    ├── logging/             # Logger 實例
    └── exception/           # 自訂例外與錯誤標籤
```

## 已測試平台

- Windows 10 / 11
- macOS 10.15 ~ 11（Big Sur）
- Ubuntu 20.04
- Raspberry Pi 3B+

## 授權條款

本專案採用 [MIT 授權條款](../LICENSE)。

## 貢獻指南

請參閱 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解貢獻規範。

## 相關連結

- **PyPI**：https://pypi.org/project/je_load_density/
- **文件**：https://loaddensity.readthedocs.io/en/latest/
- **原始碼**：https://github.com/Intergration-Automation-Testing/LoadDensity
