測試紀錄
========

概觀
----

``test_record_instance`` 為 Locust ``request`` hook 寫入的記憶體紀錄。所有報告產生器（HTML / JSON / XML / CSV / JUnit / summary）都從此物件讀取，SQLite 持久化 helper 將其寫入磁碟。

紀錄欄位
--------

每筆紀錄為 dict，欄位如下：

* ``Method`` — HTTP method 或協定標籤（``GET``、``POST``、``WS``、``GRPC``、``MQTT``、``TCP``、``UDP``）。
* ``test_url`` — 目標 URL 或位址。
* ``name`` — Locust 事件名（未指定時為 ``request_url``）。
* ``status_code`` — 回應 status（字串）或 ``None``。
* ``response_time_ms`` — Locust 回報的回應時間（ms）。
* ``response_length`` — 回應大小（bytes）。
* ``error`` — 成功為 ``None``；失敗為 exception 字串。
* ``text``、``content``、``headers`` — 選用，僅 HTTP 成功才有。

清除
----

.. code-block:: python

    from je_load_density import test_record_instance
    test_record_instance.clear_records()

或透過 executor::

    ["LD_clear_records", {}]

SQLite 持久化
-------------

見 :doc:`../sqlite_persistence/sqlite_persistence_doc`。
