HTTP 使用者
===========

概觀
----

LoadDensity 內含兩個 HTTP user 模板，皆透過 ``request_executor`` 與 ``scenario_runner`` 連線：

* ``http_user`` — 封裝 ``locust.HttpUser``（底層 ``requests``）。
* ``fast_http_user`` — 封裝 ``locust.FastHttpUser``（底層 geventhttpclient，吞吐高得多）。

高負載情境選 ``fast_http_user``。需要 ``requests`` 特性或 middleware 時用 ``http_user``。

Task 欄位
---------

每個 HTTP task 是 dict；runner 將下列欄位轉送底層 client，其餘欄位忽略。

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 欄位
     - 意義
   * - ``method``
     - ``get`` / ``post`` / ``put`` / ``patch`` / ``delete`` / ``head`` /
       ``options``（不分大小寫）。
   * - ``request_url`` / ``url``
     - 目標 URL（絕對或相對 ``host``）。
   * - ``name``
     - Locust 事件名；預設等同 URL。
   * - ``headers``
     - 請求 headers dict。
   * - ``params``
     - Query string 參數（dict 或 list of pairs）。
   * - ``json``
     - 以 JSON 序列化的 body。
   * - ``data``
     - Form-encoded body（dict / list / str）。
   * - ``cookies``
     - cookies dict。
   * - ``timeout``
     - 單請求 timeout（秒）。
   * - ``allow_redirects``、``verify``、``files``
     - 直接轉送 client。
   * - ``auth``
     - ``{"type": "basic", "username": "...", "password": "..."}`` 或
       ``{"type": "bearer", "token": "..."}``。
   * - ``assertions``
     - 回應斷言（見 :doc:`../assertions/assertions_doc`）。
   * - ``extract``
     - 回應擷取（見 :doc:`../parameter_resolver/parameter_resolver_doc`）。
   * - ``weight``、``run_if``、``skip_if``
     - 情境流程控制（見 :doc:`../scenarios/scenarios_doc`）。

範例
----

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=60,
        variables={"base": "https://api.example.com"},
        tasks=[
            {"method": "post", "request_url": "${var.base}/login",
             "json": {"email": "u@example.com", "password": "secret"},
             "extract": [
                 {"var": "auth", "from": "json_path", "path": "data.token"}
             ]},
            {"method": "get", "request_url": "${var.base}/profile",
             "headers": {"Authorization": "Bearer ${var.auth}"},
             "assertions": [{"type": "status_code", "value": 200}]},
        ],
    )
