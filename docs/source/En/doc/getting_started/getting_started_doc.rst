Getting Started
===============

This guide walks you through the basics of running your first
LoadDensity load test.

User types
----------

LoadDensity ships six user templates:

* ``fast_http_user`` — high-throughput HTTP (``locust.FastHttpUser`` +
  geventhttpclient).
* ``http_user`` — ``locust.HttpUser`` + ``requests``.
* ``websocket_user``, ``grpc_user``, ``mqtt_user``, ``socket_user`` —
  see Chapter 4.

Run a test (Python API)
-----------------------

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

Launch the Locust Web UI
------------------------

.. code-block:: python

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50, spawn_rate=10, test_time=30,
        web_ui_dict={"host": "127.0.0.1", "port": 8089},
        tasks=[{"method": "get", "request_url": "https://httpbin.org/get"}],
    )

Then open ``http://127.0.0.1:8089`` in your browser.

Run a JSON action script
------------------------

Create ``test_scenario.json``:

.. code-block:: json

    {"load_density": [
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "user_count": 20, "spawn_rate": 10, "test_time": 30,
        "tasks": [{"method": "get", "request_url": "https://httpbin.org/get"}]
      }],
      ["LD_generate_summary_report", {"report_name": "smoke"}]
    ]}

Execute via the CLI::

    python -m je_load_density run test_scenario.json

Or from Python:

.. code-block:: python

    from je_load_density import execute_action, read_action_json
    execute_action(read_action_json("test_scenario.json"))

JSON script format
~~~~~~~~~~~~~~~~~~

Each action is a list:

* with keyword arguments: ``["action_name", {"param1": "value1"}]``
* with positional arguments: ``["action_name", ["arg1", "arg2"]]``
* with no arguments: ``["action_name"]``

The top-level document is either a bare action list or a
``{"load_density": [...]}`` wrapper.

Next steps
----------

* Parameterise scripts: see :doc:`../parameter_resolver/parameter_resolver_doc`.
* Layer scenario flow: see :doc:`../scenarios/scenarios_doc`.
* Run a distributed master/worker fleet:
  see :doc:`../distributed/distributed_doc`.
* Ship metrics to Prometheus / InfluxDB / OTel:
  see :doc:`../metrics/metrics_doc`.
