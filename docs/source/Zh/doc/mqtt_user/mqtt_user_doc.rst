MQTT 使用者
===========

概觀
----

MQTT user 模板對 MQTT broker 進行 ``connect`` / ``publish`` / ``subscribe`` / ``disconnect``。底層使用 ``paho-mqtt``，lazy import — 以 ``pip install je_load_density[mqtt]`` 安裝。

Task 欄位
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 欄位
     - 意義
   * - ``method``
     - ``connect`` / ``publish`` / ``subscribe`` / ``disconnect``。
   * - ``broker`` / ``host``
     - MQTT broker 的 ``host:port``。
   * - ``topic``
     - 發佈／訂閱主題。
   * - ``payload``
     - publish body（``str`` 或 ``bytes``）。
   * - ``qos``
     - 0 / 1 / 2。
   * - ``retain``
     - 布林。
   * - ``username`` / ``password``
     - 憑證。
   * - ``client_id``
     - 選用 client id（預設為隨機十六進位字串）。
   * - ``timeout``
     - publish 等待 timeout（預設 5 秒）。

範例
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "mqtt_user"},
        user_count=10,
        spawn_rate=5,
        test_time=60,
        tasks=[
            {"method": "connect", "broker": "127.0.0.1:1883"},
            {"method": "subscribe", "topic": "telemetry/in", "qos": 1},
            {"method": "publish", "topic": "telemetry/out",
             "payload": "ping", "qos": 1},
            {"method": "disconnect"},
        ],
    )

每個步驟會觸發標記為 ``MQTT`` 的 Locust 事件。
