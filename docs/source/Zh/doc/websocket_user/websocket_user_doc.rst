WebSocket 使用者
================

概觀
----

WebSocket user 模板對指定的 ``ws://`` / ``wss://`` URL 做 connect / send / recv 迴圈。底層使用 ``websocket-client``，採 lazy import — 以 ``pip install je_load_density[websocket]`` 安裝。

Task 欄位
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 欄位
     - 意義
   * - ``method``
     - ``connect`` / ``send`` / ``recv`` / ``sendrecv`` / ``close``。
   * - ``request_url`` / ``url``
     - WebSocket URL（``connect`` 必填，其餘步驟可重用上次連線）。
   * - ``name``
     - 事件名；預設為 URL 或 method。
   * - ``payload``
     - 要送出的字串 / bytes。
   * - ``expect``
     - 對接收到的 frame 做 substring 斷言。
   * - ``timeout``
     - 接收 timeout（秒），預設 5。

範例
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "websocket_user"},
        user_count=10,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"method": "connect", "request_url": "wss://echo.example.com/socket"},
            {"method": "sendrecv", "payload": '{"ping": 1}', "expect": "pong"},
            {"method": "close"},
        ],
    )

每個步驟會觸發標記為 ``WS`` 的 Locust 事件，供統計彙整。
