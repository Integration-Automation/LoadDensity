# LoadDensity

[![Python](https://img.shields.io/pypi/pyversions/je_load_density)](https://pypi.org/project/je_load_density/)
[![PyPI](https://img.shields.io/pypi/v/je_load_density)](https://pypi.org/project/je_load_density/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://readthedocs.org/projects/loaddensity/badge/?version=latest)](https://loaddensity.readthedocs.io/en/latest/)

**LoadDensity** 是一个基于 [Locust](https://locust.io/) 构建的高性能负载与压力测试自动化框架。它对 Locust 的核心功能进行了简化封装，提供快速用户生成、通过模板与 JSON 脚本进行灵活测试配置、多格式报告生成（HTML / JSON / XML）、内置 GUI 图形界面、通过 TCP Socket 服务器进行远程执行，以及测试后工作流程的回调机制。

**[English](../README.md)** | **[繁體中文](README_zh-TW.md)**

---

## 功能特性

- **简化的 Locust 封装** — 将 Locust 的 `Environment`、`Runner` 和 `User` 类抽象化为简洁的高层 API。
- **两种用户类型** — 同时支持 `HttpUser` 和 `FastHttpUser`（基于 geventhttpclient，吞吐量更高）。
- **快速用户生成** — 可配置生成速率，轻松扩展至数千名并发用户。
- **JSON 驱动的测试脚本** — 将测试场景定义为 JSON 文件，无需编写 Python 代码即可执行。
- **动作执行器** — 内置的事件驱动执行器，将动作名称映射到函数。支持批量执行与文件驱动执行。
- **报告生成** — 导出三种格式的测试结果：
  - **HTML** — 包含成功/失败记录的样式化表格
  - **JSON** — 适合程序化处理的结构化数据
  - **XML** — 标准 XML 输出，适合 CI/CD 集成
- **请求钩子** — 自动记录每个请求（成功与失败），包含方法、URL、状态码、响应内容、头部与错误信息。
- **回调执行器** — 将触发函数与回调函数串联，用于测试后工作流程（例如：执行测试后自动生成报告）。
- **TCP Socket 服务器** — 基于 gevent 的远程执行服务器。通过 TCP 接收 JSON 命令以远程执行测试。
- **项目脚手架** — 自动生成项目目录结构，包含关键字模板与执行器脚本。
- **包管理器** — 在运行时动态加载外部 Python 包，并将其函数注册到执行器中。
- **GUI 图形界面（可选）** — 基于 PySide6 的图形界面，支持实时日志显示，提供英文与繁体中文界面。
- **CLI 命令行支持** — 直接从命令行执行测试、运行脚本或创建项目结构。
- **跨平台** — 支持 Windows、macOS 和 Linux。

## 安装

### 基本安装（CLI 与库）

```bash
pip install je_load_density
```

### 包含 GUI 支持

```bash
pip install je_load_density[gui]
```

这会安装 [PySide6](https://doc.qt.io/qtforpython/) 和 [qt-material](https://github.com/UN-GCPDS/qt-material) 以提供图形界面。

## 系统要求

- Python **3.10** 或更高版本
- [Locust](https://locust.io/)（会作为依赖项自动安装）

## 快速上手

### 1. 使用 Python API

```python
from je_load_density import start_test

# 定义用户配置与任务
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

**参数说明：**
| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `user_detail_dict` | `dict` | — | 用户类型配置。`{"user": "fast_http_user"}` 或 `{"user": "http_user"}` |
| `user_count` | `int` | `50` | 模拟用户总数 |
| `spawn_rate` | `int` | `10` | 每秒生成的用户数量 |
| `test_time` | `int` | `60` | 测试持续时间（秒）。设为 `None` 则无限执行 |
| `web_ui_dict` | `dict` | `None` | 启用 Locust Web UI，例如 `{"host": "127.0.0.1", "port": 8089}` |
| `tasks` | `dict` | — | HTTP 方法对应请求 URL 的映射 |

### 2. 使用 JSON 脚本文件

创建 JSON 文件（`test_scenario.json`）：

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

从 Python 执行：

```python
from je_load_density import execute_action, read_action_json

execute_action(read_action_json("test_scenario.json"))
```

### 3. 使用 CLI 命令行

```bash
# 执行单个 JSON 脚本文件
python -m je_load_density -e test_scenario.json

# 执行目录中所有 JSON 文件
python -m je_load_density -d ./test_scripts/

# 执行内联 JSON 字符串
python -m je_load_density --execute_str '[["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}, "user_count": 10, "spawn_rate": 5, "test_time": 5, "tasks": {"get": {"request_url": "http://httpbin.org/get"}}}]]'

# 使用模板创建新项目
python -m je_load_density -c MyProject
```

### 4. 使用 GUI 图形界面

```python
from je_load_density.gui.main_window import LoadDensityUI
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = LoadDensityUI()
window.show()
sys.exit(app.exec())
```

## 报告生成

执行测试后，从记录的数据生成报告：

```python
from je_load_density import (
    generate_html_report,
    generate_json_report,
    generate_xml_report,
)

# HTML 报告 — 创建 "my_report.html"
generate_html_report("my_report")

# JSON 报告 — 创建 "my_report_success.json" 和 "my_report_failure.json"
generate_json_report("my_report")

# XML 报告 — 创建 "my_report_success.xml" 和 "my_report_failure.xml"
generate_xml_report("my_report")
```

## 高级用法

### 动作执行器

执行器将字符串动作名称映射到可调用的函数。所有 Python 内置函数也可使用。

```python
from je_load_density import executor, add_command_to_executor

# 注册自定义函数
def my_custom_action(message):
    print(f"自定义动作: {message}")

add_command_to_executor({"my_action": my_custom_action})

# 程序化执行动作
executor.execute_action([
    ["my_action", ["Hello World"]],
    ["print", ["测试完成"]],
])
```

**内置执行器动作：**
| 动作名称 | 说明 |
|---|---|
| `LD_start_test` | 启动负载测试 |
| `LD_generate_html` | 生成 HTML 片段 |
| `LD_generate_html_report` | 生成完整 HTML 报告文件 |
| `LD_generate_json` | 生成 JSON 数据结构 |
| `LD_generate_json_report` | 生成 JSON 报告文件 |
| `LD_generate_xml` | 生成 XML 字符串 |
| `LD_generate_xml_report` | 生成 XML 报告文件 |
| `LD_execute_action` | 执行动作列表 |
| `LD_execute_files` | 从多个文件执行动作 |
| `LD_add_package_to_executor` | 动态加载包到执行器 |

### 回调执行器

将触发函数与回调串联：

```python
from je_load_density import callback_executor

def after_test():
    print("测试完成，正在生成报告...")

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

### TCP Socket 服务器（远程执行）

启动接收 JSON 命令的 TCP 服务器：

```python
from je_load_density import start_load_density_socket_server

# 启动服务器（阻塞式）
start_load_density_socket_server(host="localhost", port=9940)
```

从客户端发送命令：

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

发送 `"quit_server"` 可优雅地关闭服务器。

### 项目脚手架

生成包含关键字模板与执行器脚本的项目：

```python
from je_load_density import create_project_dir

create_project_dir(project_path="./my_tests", parent_name="LoadDensity")
```

这会创建以下结构：
```
my_tests/
└── LoadDensity/
    ├── keyword/
    │   ├── keyword1.json    # FastHttpUser 测试模板
    │   └── keyword2.json    # HttpUser 测试模板
    └── executor/
        ├── executor_one_file.py   # 执行单个关键字文件
        └── executor_folder.py     # 执行 keyword/ 目录中所有文件
```

### 动态包加载

加载外部包并将其函数注册到执行器中：

```python
from je_load_density import executor

# 加载包并使其函数可作为执行器动作使用
executor.execute_action([
    ["LD_add_package_to_executor", ["my_custom_package"]]
])
```

### 测试记录

以程序化方式访问原始测试记录：

```python
from je_load_density import test_record_instance

# 执行测试后
for record in test_record_instance.test_record_list:
    print(record["Method"], record["test_url"], record["status_code"])

for error in test_record_instance.error_record_list:
    print(error["Method"], error["test_url"], error["error"])

# 清除记录
test_record_instance.clear_records()
```

## 架构

```
je_load_density/
├── __init__.py              # 公开 API 导出
├── __main__.py              # CLI 入口点
├── gui/                     # PySide6 GUI（可选依赖）
│   ├── main_window.py       # 主窗口（QMainWindow）
│   ├── main_widget.py       # 测试参数表单与日志面板
│   ├── load_density_gui_thread.py  # 测试后台线程
│   ├── log_to_ui_filter.py  # GUI 显示的日志拦截器
│   └── language_wrapper/    # 国际化（英文、繁体中文）
├── wrapper/
│   ├── create_locust_env/   # Locust Environment 与 Runner 设置
│   ├── start_wrapper/       # 高层 start_test() 入口点
│   ├── user_template/       # HttpUser 与 FastHttpUser 封装
│   ├── proxy/               # 用户代理容器与配置
│   └── event/               # 请求钩子（记录所有请求）
└── utils/
    ├── executor/            # 动作执行器（事件驱动）
    ├── generate_report/     # HTML、JSON、XML 报告生成器
    ├── test_record/         # 测试记录存储
    ├── socket_server/       # 远程执行 TCP 服务器
    ├── callback/            # 回调函数执行器
    ├── project/             # 项目脚手架与模板
    ├── package_manager/     # 动态包加载
    ├── json/                # JSON 文件读写工具
    ├── xml/                 # XML 结构工具
    ├── file_process/        # 目录文件列表
    ├── logging/             # Logger 实例
    └── exception/           # 自定义异常与错误标签
```

## 已测试平台

- Windows 10 / 11
- macOS 10.15 ~ 11（Big Sur）
- Ubuntu 20.04
- Raspberry Pi 3B+

## 许可证

本项目采用 [MIT 许可证](../LICENSE)。

## 贡献指南

请参阅 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解贡献规范。

## 相关链接

- **PyPI**：https://pypi.org/project/je_load_density/
- **文档**：https://loaddensity.readthedocs.io/en/latest/
- **源代码**：https://github.com/Intergration-Automation-Testing/LoadDensity
