start_test 與 prepare_env
=========================

概觀
----

``start_test`` 是高層進入點，挑選 user 模板、種入參數解析器、請 ``prepare_env`` 以指定模式（local / master / worker）建立 Locust 環境。

簽章
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=60,
        web_ui_dict=None,                 # {"host": "...", "port": ...}
        runner_mode="local",              # "local" | "master" | "worker"
        master_bind_host="*",
        master_bind_port=5557,
        master_host="127.0.0.1",
        master_port=5557,
        expected_workers=0,
        tasks=...,
        variables={"host": "https://api.example.com"},
        csv_sources=[{"name": "users", "file_path": "users.csv"}],
    )

支援的 user 類型
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``user``
     - 模板
   * - ``http_user``
     - ``locust.HttpUser`` 封裝（以 ``requests`` 為底）。
   * - ``fast_http_user``
     - ``locust.FastHttpUser`` 封裝（以 ``geventhttpclient`` 為底）。
   * - ``websocket_user``
     - WebSocket 框架收送迴圈（lazy import ``websocket-client``）。
   * - ``grpc_user``
     - 對 operator 提供的 stub 進行 unary gRPC 呼叫。
   * - ``mqtt_user``
     - MQTT 發佈／訂閱迴圈。
   * - ``socket_user``
     - 原生 TCP / UDP 收送。

prepare_env
-----------

``prepare_env`` 是 ``start_test`` 之下的較低階 API。當你想自行整合至其他 runner 時較有用。

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

分散式模式
----------

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

Worker（在每個壓測節點執行，與 master 同網段）::

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="worker",
        master_host="10.0.0.10",
        master_port=5557,
        tasks=[...],
    )

Master 在開始 ramp 前會等待 ``expected_workers`` 個 worker 註冊完成。Workers 加入 master 後，會依群集規模分擔 user count。
