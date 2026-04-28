入門
====

本指南帶你跑出第一支 LoadDensity 壓測。

User 類型
---------

LoadDensity 提供六種 user 類型：

* ``fast_http_user`` — 高吞吐 HTTP（``locust.FastHttpUser`` + geventhttpclient）。
* ``http_user`` — ``locust.HttpUser`` + ``requests``。
* ``websocket_user``、``grpc_user``、``mqtt_user``、``socket_user`` — 詳見第 4 章。

以 Python API 執行
------------------

.. code-block:: python

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

啟動 Locust Web UI
------------------

.. code-block:: python

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50, spawn_rate=10, test_time=30,
        web_ui_dict={"host": "127.0.0.1", "port": 8089},
        tasks=[{"method": "get", "request_url": "https://httpbin.org/get"}],
    )

之後在瀏覽器開啟 ``http://127.0.0.1:8089``。

以 JSON 動作腳本執行
--------------------

建立 ``test_scenario.json``：

.. code-block:: json

    {"load_density": [
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "user_count": 20, "spawn_rate": 10, "test_time": 30,
        "tasks": [{"method": "get", "request_url": "https://httpbin.org/get"}]
      }],
      ["LD_generate_summary_report", {"report_name": "smoke"}]
    ]}

執行::

    python -m je_load_density run test_scenario.json

或於 Python：

.. code-block:: python

    from je_load_density import execute_action, read_action_json
    execute_action(read_action_json("test_scenario.json"))

下一步
------

* 為動作腳本參數化：見 :doc:`../parameter_resolver/parameter_resolver_doc`。
* 改用情境流程：見 :doc:`../scenarios/scenarios_doc`。
* 升級到分散式 master/worker：見 :doc:`../distributed/distributed_doc`。
* 啟動 Prometheus / InfluxDB / OTel 指標 sink：見 :doc:`../metrics/metrics_doc`。
