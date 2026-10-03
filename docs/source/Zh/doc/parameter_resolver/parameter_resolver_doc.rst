參數解析器
==========

概觀
----

參數解析器會展開任何巢狀 string / list / dict 結構中的 ``${...}`` 占位符。在每個 task 被 user 模板處理之前自動套用，讓資料能在動作之間順暢流動。

支援的占位符
------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 占位符
     - 解析為
   * - ``${var.NAME}``
     - 由 ``register_variable`` / ``register_variables`` 設定的值。
   * - ``${env.NAME}``
     - 環境變數 ``NAME``。
   * - ``${csv.SOURCE.COLUMN}``
     - CSV 來源 ``SOURCE`` 的下一筆資料中欄位 ``COLUMN`` 的值（預設循環）。
   * - ``${faker.METHOD}``
     - 呼叫 ``Faker().METHOD()``（lazy import，選用相依）。
   * - ``${uuid()}``
     - 新的 UUID 4 字串。
   * - ``${now()}``
     - 本地 ISO-8601 時間（秒）。
   * - ``${randint(min, max)}``
     - 介於 ``[min, max]`` 之間、密碼學強度的隨機整數。

未知占位符會原樣保留，便於 dry run 時偵測缺值。

使用者隔離
----------

HTTP、FastHTTP 與 Locust HTTPX 使用者各自 fork 變數及 session 狀態。
擷取規則的 ``scope: "session"`` 對應獨立的 ``${session.NAME}``；
省略 scope 則寫入目前使用者的 ``${var.NAME}``。
其他協定模板保留既有 scope。
Python 可用 ``with use_resolver(get_resolver().fork()):`` 選擇解析器；
巢狀 scope 在例外後也會還原。每次遞迴 ``resolve(task)`` 對每個
CSV／DB 來源只取一列，欄位保持配對，使用者間同步分配資料列。

註冊資料
--------

.. code-block:: python

    from je_load_density import (
        register_variable, register_variables,
        register_csv_source, register_csv_sources,
    )

    register_variable("base", "https://api.example.com")
    register_variables({"token": "abc", "tenant": "acme"})

    register_csv_source("users", "users.csv")            # 循環
    register_csv_sources([
        {"name": "products", "file_path": "products.csv", "cycle": False},
    ])

CSV 必須有 header；每次 ``resolve(task)`` 對每個來源取一列，該 task
所有欄位共用這列資料，下次 resolve 才會前進。

動作 JSON 用法
--------------

.. code-block:: json

    {"load_density": [
      ["LD_register_variables", {"variables": {"base": "https://api.example.com"}}],
      ["LD_register_csv_sources", {"sources": [
        {"name": "users", "file_path": "users.csv"}
      ]}],
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "tasks": [{
          "method": "post",
          "request_url": "${var.base}/login",
          "json": {"email": "${csv.users.email}", "password": "${csv.users.password}"}
        }]
      }]
    ]}

從回應擷取值
------------

HTTP task 可以宣告 ``extract`` 規則；命中的值會寫回解析器：

.. code-block:: json

    {
      "method": "post",
      "request_url": "${var.base}/login",
      "json": {"email": "u@example.com", "password": "secret"},
      "extract": [
        {"var": "auth_token", "from": "json_path", "path": "data.token"},
        {"var": "request_id", "from": "header", "name": "X-Request-Id"},
        {"var": "status", "from": "status_code"}
      ]
    }

後續 task 即可用 ``${var.auth_token}`` 取用。

清除
----

呼叫 ``parameter_resolver.clear()``（或 ``LD_clear_resolver``）以清除累積狀態。
