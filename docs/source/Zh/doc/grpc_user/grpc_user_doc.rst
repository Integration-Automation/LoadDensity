gRPC 使用者
===========

概觀
----

gRPC user 模板對 operator 提供的 stub 進行 unary 呼叫。底層使用 ``grpcio`` 與你自己的 ``*_pb2`` / ``*_pb2_grpc``，皆 lazy import — 以 ``pip install je_load_density[grpc]`` 安裝。

Task 欄位
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 欄位
     - 意義
   * - ``target`` / ``host``
     - gRPC 端點，如 ``localhost:50051``。
   * - ``stub_path``
     - Stub 類別的 dotted path（``pkg.greeter_pb2_grpc.GreeterStub``）。
   * - ``request_path``
     - 請求訊息的 dotted path（``pkg.greeter_pb2.HelloRequest``）。
   * - ``method``
     - Stub 上的 method 名。
   * - ``payload``
     - 用以建構 request message 的 dict。
   * - ``metadata``
     - ``[key, value]`` pair 列表或扁平 dict。
   * - ``timeout``
     - 單呼叫 timeout（秒），預設 10。

dotted path 在 ``importlib.import_module`` 之前會通過嚴格識別符 regex 驗證；traversal 攻擊（``../``、``;``、``__import__``）皆被拒絕。

範例
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "grpc_user"},
        user_count=20,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {
                "name": "say_hello",
                "target": "localhost:50051",
                "stub_path": "pkg.greeter_pb2_grpc.GreeterStub",
                "request_path": "pkg.greeter_pb2.HelloRequest",
                "method": "SayHello",
                "payload": {"name": "world"},
                "metadata": [["x-token", "abc"]],
                "timeout": 5,
            }
        ],
    )

每次呼叫會觸發標記為 ``GRPC`` 的 Locust 事件。
