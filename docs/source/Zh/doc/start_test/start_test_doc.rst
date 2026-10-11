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

原生 asyncio HTTP
-----------------

公開 ``start_test`` 與 ``LD_start_test`` 可傳入 ``engine="asyncio"``；
預設仍為 Locust。現有 event loop 請用 ``await run_async_load(...)``。
套件及原生匯入不載入 Locust，也不修改 socket／TLS／threading。
Locust 會修改所處直譯器；之後執行原生 I/O 請用獨立行程，CLI bench
及桌面 supervisor 均提供此隔離。
支援請求參數、body、header、cookie、auth、redirect、五種 HTTP 斷言、
三種擷取、獨立使用者 session、sequence／weighted／conditional、重試、
非同步 think time／token bucket、ramp 及 stages／spike／soak。
每位使用者重用 TLS／proxy client，憑證不修改其他使用者的 trust context。
自訂 SSLContext 請直接配置憑證並省略 cert／client_cert。
無效或未支援設定在請求前拒絕；非 HTTP 協定、master／worker 與
metrics exporter 對等仍待補齊。數量、速率、期間須為正數且有限，數量須為整數。

``AsyncRunHandle`` 提供 awaitable ``start``／``wait`` 及 ``stop``／``snapshot``。
兩個引擎均支援 ``stop_requested`` 與 ``on_environment`` callback。
取消會關閉 task／client；worker／清理例外會向上傳遞。
每次回傳獨立 ``summary`` 可交給 SLA 評估，既有報告清單與選用 canonical
RunContext 仍相容。``requests`` 是成功次數，``summary.totals.requests``
是所有量測次數。HTTP 4xx／5xx 計為失敗，除非 status-code 斷言明確通過。

Canonical 分散式結果
--------------------

Master 從 ``je_load_density.utils.test_record.distributed_context`` 匯入
``DistributedRunContext`` 並傳入 ``run_context=DistributedRunContext()``，
每個 worker 設 ``distributed_records=True``；需協調中的 ActionCore
record API，既有 legacy 環境仍相容於已發布的相依下限。
Master 保留 worker 身分，整批驗證後才寫入，依 record ID 全域去重。
新接受的紀錄只寫入既有報告一次，診斷見 ``env.record_delivery.snapshot()``。

預設每批 100 筆／262144 bytes、每筆 65536 bytes、待送 1000 筆／4194304
bytes、重試間隔 0.1 秒，drain／terminal acknowledgement 各最多 2 秒。
可用 ``record_batch_size``、``record_batch_bytes``、``record_max_bytes``、
``record_max_pending``、``record_pending_bytes``、``record_flush_interval``、
``record_drain_timeout`` 調整。超額、重試衝突及最後傳送不完整均明確失敗。
資料留在記憶體直到匯出；持續使用者重新分配不重播請求、不搬移 session，
也不提供 finite shards／exactly-once 執行。
