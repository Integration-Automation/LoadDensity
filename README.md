# LoadDensity

[![Python](https://img.shields.io/pypi/pyversions/je_load_density)](https://pypi.org/project/je_load_density/)
[![PyPI](https://img.shields.io/pypi/v/je_load_density)](https://pypi.org/project/je_load_density/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://readthedocs.org/projects/loaddensity/badge/?version=latest)](https://loaddensity.readthedocs.io/en/latest/)

**LoadDensity** is a high-performance load & stress testing automation framework built on top of [Locust](https://locust.io/). It provides a simplified wrapper around Locust's core functionality, enabling fast user spawning, flexible test configuration via templates and JSON-driven scripts, report generation in multiple formats (HTML / JSON / XML), a built-in GUI, remote execution via TCP socket server, and a callback mechanism for post-test workflows.

**[繁體中文](README/README_zh-TW.md)** | **[简体中文](README/README_zh-CN.md)**

---

## Features

- **Simplified Locust Wrapper** — Abstracts Locust's `Environment`, `Runner`, and `User` classes behind a clean, high-level API.
- **Two User Types** — Supports both `HttpUser` and `FastHttpUser` (geventhttpclient-based, higher throughput).
- **Fast User Spawning** — Scale to thousands of concurrent users with configurable spawn rate.
- **JSON-Driven Test Scripts** — Define test scenarios as JSON files and execute them without writing Python code.
- **Action Executor** — A built-in event-driven executor that maps action names to functions. Supports batch execution and file-driven execution.
- **Report Generation** — Export test results in three formats:
  - **HTML** — Styled tables with success/failure records
  - **JSON** — Structured data for programmatic consumption
  - **XML** — Standard XML output for CI/CD integration
- **Request Hook** — Automatically records every request (success and failure) with method, URL, status code, response body, headers, and errors.
- **Callback Executor** — Chain a trigger function with a callback function for post-test workflows (e.g., run test then generate report).
- **TCP Socket Server** — Remote execution server based on gevent. Accepts JSON commands over TCP to execute tests remotely.
- **Project Scaffolding** — Auto-generate project directory structure with keyword templates and executor scripts.
- **Package Manager** — Dynamically load external Python packages and register their functions into the executor at runtime.
- **GUI (Optional)** — PySide6-based graphical interface with real-time log display, supporting English and Traditional Chinese.
- **CLI Support** — Run tests, execute scripts, or scaffold projects directly from the command line.
- **Cross-Platform** — Works on Windows, macOS, and Linux.

## Installation

### Basic (CLI & Library)

```bash
pip install je_load_density
```

### With GUI Support

```bash
pip install je_load_density[gui]
```

This installs [PySide6](https://doc.qt.io/qtforpython/) and [qt-material](https://github.com/UN-GCPDS/qt-material) for the graphical interface.

## Requirements

- Python **3.10** or later
- [Locust](https://locust.io/) (installed automatically as a dependency)

## Quick Start

### 1. Using the Python API

```python
from je_load_density import start_test

# Define user configuration and tasks
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

**Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `user_detail_dict` | `dict` | — | User type configuration. `{"user": "fast_http_user"}` or `{"user": "http_user"}` |
| `user_count` | `int` | `50` | Total number of simulated users |
| `spawn_rate` | `int` | `10` | Number of users spawned per second |
| `test_time` | `int` | `60` | Test duration in seconds. `None` for unlimited |
| `web_ui_dict` | `dict` | `None` | Enable Locust Web UI, e.g. `{"host": "127.0.0.1", "port": 8089}` |
| `tasks` | `dict` | — | HTTP method to request URL mapping |

### 2. Using JSON Script Files

Create a JSON file (`test_scenario.json`):

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

Execute from Python:

```python
from je_load_density import execute_action, read_action_json

execute_action(read_action_json("test_scenario.json"))
```

### 3. Using the CLI

```bash
# Execute a single JSON script file
python -m je_load_density -e test_scenario.json

# Execute all JSON files in a directory
python -m je_load_density -d ./test_scripts/

# Execute an inline JSON string
python -m je_load_density --execute_str '[["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}, "user_count": 10, "spawn_rate": 5, "test_time": 5, "tasks": {"get": {"request_url": "http://httpbin.org/get"}}}]]'

# Scaffold a new project with templates
python -m je_load_density -c MyProject
```

### 4. Using the GUI

```python
from je_load_density.gui.main_window import LoadDensityUI
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = LoadDensityUI()
window.show()
sys.exit(app.exec())
```

## Report Generation

After running a test, generate reports from the recorded data:

```python
from je_load_density import (
    generate_html_report,
    generate_json_report,
    generate_xml_report,
)

# HTML report — creates "my_report.html"
generate_html_report("my_report")

# JSON report — creates "my_report_success.json" and "my_report_failure.json"
generate_json_report("my_report")

# XML report — creates "my_report_success.xml" and "my_report_failure.xml"
generate_xml_report("my_report")
```

## Advanced Usage

### Action Executor

The executor maps string action names to callable functions. All built-in Python functions are also available.

```python
from je_load_density import executor, add_command_to_executor

# Register a custom function
def my_custom_action(message):
    print(f"Custom: {message}")

add_command_to_executor({"my_action": my_custom_action})

# Execute actions programmatically
executor.execute_action([
    ["my_action", ["Hello World"]],
    ["print", ["Test complete"]],
])
```

**Built-in executor actions:**
| Action Name | Description |
|---|---|
| `LD_start_test` | Start a load test |
| `LD_generate_html` | Generate HTML fragments |
| `LD_generate_html_report` | Generate full HTML report file |
| `LD_generate_json` | Generate JSON data structure |
| `LD_generate_json_report` | Generate JSON report files |
| `LD_generate_xml` | Generate XML strings |
| `LD_generate_xml_report` | Generate XML report files |
| `LD_execute_action` | Execute a list of actions |
| `LD_execute_files` | Execute actions from multiple files |
| `LD_add_package_to_executor` | Dynamically load a package into the executor |

### Callback Executor

Chain a trigger function with a callback:

```python
from je_load_density import callback_executor

def after_test():
    print("Test finished, generating report...")

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

### TCP Socket Server (Remote Execution)

Start a TCP server that accepts JSON commands:

```python
from je_load_density import start_load_density_socket_server

# Start server (blocking)
start_load_density_socket_server(host="localhost", port=9940)
```

Send commands from a client:

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

Send `"quit_server"` to gracefully shut down the server.

### Project Scaffolding

Generate a project with keyword templates and executor scripts:

```python
from je_load_density import create_project_dir

create_project_dir(project_path="./my_tests", parent_name="LoadDensity")
```

This creates:
```
my_tests/
└── LoadDensity/
    ├── keyword/
    │   ├── keyword1.json    # FastHttpUser test template
    │   └── keyword2.json    # HttpUser test template
    └── executor/
        ├── executor_one_file.py   # Execute single keyword file
        └── executor_folder.py     # Execute all files in keyword/
```

### Dynamic Package Loading

Load external packages and register their functions into the executor:

```python
from je_load_density import executor

# Load a package and make its functions available as executor actions
executor.execute_action([
    ["LD_add_package_to_executor", ["my_custom_package"]]
])
```

### Test Records

Access raw test records programmatically:

```python
from je_load_density import test_record_instance

# After running a test
for record in test_record_instance.test_record_list:
    print(record["Method"], record["test_url"], record["status_code"])

for error in test_record_instance.error_record_list:
    print(error["Method"], error["test_url"], error["error"])

# Clear records
test_record_instance.clear_records()
```

## Architecture

```
je_load_density/
├── __init__.py              # Public API exports
├── __main__.py              # CLI entry point
├── gui/                     # PySide6 GUI (optional dependency)
│   ├── main_window.py       # Main window (QMainWindow)
│   ├── main_widget.py       # Test parameter form & log panel
│   ├── load_density_gui_thread.py  # Background thread for tests
│   ├── log_to_ui_filter.py  # Log interceptor for GUI display
│   └── language_wrapper/    # i18n (English, Traditional Chinese)
├── wrapper/
│   ├── create_locust_env/   # Locust Environment & Runner setup
│   ├── start_wrapper/       # High-level start_test() entry point
│   ├── user_template/       # HttpUser & FastHttpUser wrappers
│   ├── proxy/               # User proxy container & configuration
│   └── event/               # Request hook (records all requests)
└── utils/
    ├── executor/            # Action executor (event-driven)
    ├── generate_report/     # HTML, JSON, XML report generators
    ├── test_record/         # Test record storage
    ├── socket_server/       # TCP server for remote execution
    ├── callback/            # Callback function executor
    ├── project/             # Project scaffolding & templates
    ├── package_manager/     # Dynamic package loading
    ├── json/                # JSON file read/write utilities
    ├── xml/                 # XML structure utilities
    ├── file_process/        # Directory file listing
    ├── logging/             # Logger instance
    └── exception/           # Custom exceptions & error tags
```

## Tested Platforms

- Windows 10 / 11
- macOS 10.15 ~ 11 (Big Sur)
- Ubuntu 20.04
- Raspberry Pi 3B+

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Links

- **PyPI**: https://pypi.org/project/je_load_density/
- **Documentation**: https://loaddensity.readthedocs.io/en/latest/
- **Source Code**: https://github.com/Intergration-Automation-Testing/LoadDensity
