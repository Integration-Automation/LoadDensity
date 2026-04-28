原生 TCP / UDP 使用者
=====================

概觀
----

原生 socket user 模板透過 TCP 或 UDP 收送任意 bytes，並可選擇讀取有限長度的回應。使用 Python 內建 ``socket`` 模組，無需額外相依。

Task 欄位
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 欄位
     - 意義
   * - ``protocol``
     - ``tcp`` 或 ``udp``。
   * - ``target`` / ``host``
     - ``host:port``。
   * - ``payload``
     - 要送出的 bytes。字串會以 UTF-8 編碼；以 ``hex:DEADBEEF`` 字首傳入十六進位字串可送出原始 bytes。
   * - ``expect_bytes``
     - 至多讀取 N bytes 的回應（0 表示略過讀取）。
   * - ``expect_substring``
     - 對解碼後回應的 substring 斷言。
   * - ``timeout``
     - 連線／讀取 timeout（秒），預設 5。
   * - ``name``
     - 事件名；預設 ``protocol:target``。

範例
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "socket_user"},
        user_count=20,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"protocol": "tcp", "target": "127.0.0.1:9000",
             "payload": "PING\\n", "expect_bytes": 64,
             "expect_substring": "PONG"},
            {"protocol": "udp", "target": "127.0.0.1:9000",
             "payload": "hex:DEADBEEF", "expect_bytes": 4},
        ],
    )

每個步驟會觸發標記為 ``TCP`` 或 ``UDP`` 的 Locust 事件。
