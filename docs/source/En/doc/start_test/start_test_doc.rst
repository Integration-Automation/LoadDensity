start_test & prepare_env
========================

Overview
--------

``start_test`` is the high-level entrypoint that picks a user template,
seeds the parameter resolver, and asks ``prepare_env`` to build a Locust
environment in the requested mode (local / master / worker).

Signature
---------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=60,
        web_ui_dict=None,                  # {"host": "...", "port": ...}
        runner_mode="local",               # "local" | "master" | "worker"
        master_bind_host="*",
        master_bind_port=5557,
        master_host="127.0.0.1",
        master_port=5557,
        expected_workers=0,
        tasks=...,
        variables={"host": "https://api.example.com"},
        csv_sources=[{"name": "users", "file_path": "users.csv"}],
    )

Supported user types
--------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``user``
     - Template
   * - ``http_user``
     - ``locust.HttpUser`` wrapper backed by ``requests``.
   * - ``fast_http_user``
     - ``locust.FastHttpUser`` wrapper backed by ``geventhttpclient``.
   * - ``websocket_user``
     - WebSocket frame loop (lazy ``websocket-client`` import).
   * - ``grpc_user``
     - Unary gRPC calls against operator-supplied stubs.
   * - ``mqtt_user``
     - MQTT publish / subscribe loop.
   * - ``socket_user``
     - Raw TCP / UDP send-recv.

prepare_env
-----------

``prepare_env`` is the lower-level layer behind ``start_test``. It is
useful when you want to build a Locust environment manually, for
example to integrate with another runner.

.. code-block:: python

    from je_load_density import prepare_env
    from je_load_density.wrapper.user_template.fast_http_user_template import (
        FastHttpUserWrapper, set_wrapper_fasthttp_user,
    )

    set_wrapper_fasthttp_user(
        {"user": "fast_http_user"},
        tasks=[{"method": "get", "request_url": "https://example.com/"}],
    )
    prepare_env(
        user_class=FastHttpUserWrapper,
        user_count=50,
        spawn_rate=10,
        test_time=60,
        runner_mode="local",
    )

Distributed mode
----------------

Master::

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="master",
        master_bind_host="0.0.0.0",
        master_bind_port=5557,
        expected_workers=4,
        user_count=200,
        spawn_rate=20,
        test_time=300,
        tasks=[...],
    )

Worker (run on each node, on the same network as master)::

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="worker",
        master_host="10.0.0.10",
        master_port=5557,
        tasks=[...],
    )

The master waits for ``expected_workers`` workers to register before
ramping up. Workers join the master and run the requested user count
proportional to the cluster size.
