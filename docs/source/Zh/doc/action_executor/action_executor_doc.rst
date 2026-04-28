動作 Executor
=============

概觀
----

動作 executor 將指令字串對應到 callable。動作腳本是 JSON 列表，所以同一個腳本可以手寫、由 HAR 匯入產生、由 MCP 工具排程，或經由控制 socket 傳送。

所有內建指令以 ``LD_`` 為字首；安全的 Python builtin（``print``、``len``、``range`` 等）也可使用，但 ``eval``、``exec``、``compile``、``__import__``、``breakpoint``、``open``、``input`` 已被明確封鎖。

動作格式
--------

.. code-block:: python

    ["command_name"]                        # 無參數
    ["command_name", {"key": "value"}]      # 關鍵字參數
    ["command_name", [arg1, arg2]]          # 位置參數

最上層文件可為：

.. code-block:: json

    {"load_density": [["LD_start_test", {...}], ...]}

或裸列表。

範例
----

.. code-block:: python

    from je_load_density import execute_action

    execute_action({"load_density": [
        ["LD_register_variables", {"variables": {"base": "https://api.example.com"}}],
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 20,
            "spawn_rate": 10,
            "test_time": 30,
            "tasks": [{"method": "get", "request_url": "${var.base}/health"}],
        }],
        ["LD_generate_summary_report", {"report_name": "smoke"}],
    ]})

LD_* 指令
---------

下列指令於 executor 註冊。每個對應到 ``je_load_density`` 之下對應模組的實作。詳見 *Reference*。

* **核心**：``LD_start_test``、``LD_execute_action``、``LD_execute_files``、``LD_add_package_to_executor``、``LD_start_socket_server``。
* **報告**：``LD_generate_html(_report)``、``LD_generate_json(_report)``、``LD_generate_xml(_report)``、``LD_generate_csv_report``、``LD_generate_junit_report``、``LD_generate_summary_report``、``LD_summary``。
* **持久化**：``LD_persist_records``、``LD_list_runs``、``LD_fetch_run_records``、``LD_clear_records``。
* **參數解析器**：``LD_register_variable(s)``、``LD_register_csv_source(s)``、``LD_clear_resolver``。
* **錄製/重放**：``LD_load_har``、``LD_har_to_tasks``、``LD_har_to_action_json``。
* **指標 exporter**：``LD_start/stop_prometheus_exporter``、``LD_start/stop_influxdb_sink``、``LD_start/stop_opentelemetry_exporter``。

新增自訂指令
------------

.. code-block:: python

    from je_load_density import add_command_to_executor

    def slack_notify(message: str) -> None:
        ...

    add_command_to_executor({"LD_slack_notify": slack_notify})

註冊後，新指令即可在任何動作 JSON 中呼叫。
