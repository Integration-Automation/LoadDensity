HAR 錄製／重放
==============

概觀
----

HAR 匯入器把錄製的 HTTP 流量（HAR JSON）轉換為 LoadDensity tasks 列表或完整可執行的動作 JSON。可從 Chrome / Firefox DevTools、mitmproxy、Charles 等工具匯出 `HAR 1.2 <https://www.softwareishard.com/blog/har-12-spec/>`_ 格式。

Python API
----------

.. code-block:: python

    from je_load_density import load_har, har_to_tasks, har_to_action_json

    har = load_har("recording.har")
    tasks = har_to_tasks(har, include=[r"example\.com"], exclude=[r"\.svg$"])
    action_json = har_to_action_json(
        har,
        user="fast_http_user",
        user_count=20,
        spawn_rate=10,
        test_time=120,
        include=[r"api\.example\.com"],
    )

過濾
----

* ``include`` — regex 列表；URL 必須命中其一才保留。
* ``exclude`` — regex 列表；URL 命中其一即丟棄。

對應規則
--------

* HTTP method、URL、請求 headers 直接複製。
* 移除 hop-by-hop 與 HTTP/2 pseudo header（``host``、``content-length``、``connection``、``:authority`` 等）。
* JSON 請求 body（``application/json`` MIME）解析為 ``json`` 欄位；form params 變成 ``data`` dict；純文字 body 退回 ``data`` 字串。
* 擷取的 response status 變成生成 task 上的 ``status_code`` 斷言。

動作 JSON
---------

.. code-block:: json

    {"load_density": [
      ["LD_har_to_action_json", {
        "har": {"log": {...}},
        "user": "fast_http_user",
        "user_count": 20,
        "spawn_rate": 10,
        "test_time": 120
      }]
    ]}

``LD_har_to_action_json`` 的結果本身是動作 JSON，可儲存或餵給 ``LD_execute_action``。
