情境模式
========

概觀
----

HTTP / FastHttp / WebSocket user 的 tasks 可包成情境物件，控制每個 tick *要跑哪些 task*。三種模式：

* ``sequence`` — 每個 task 依序執行（預設）。
* ``weighted`` — 每 tick 依 ``weight`` 加權挑一個。
* ``conditional`` — 以 ``run_if`` / ``skip_if`` 預測式（透過參數解析器評估）控制。

格式
----

.. code-block:: json

    {
      "mode": "sequence",
      "tasks": [
        {"method": "get",  "request_url": "${var.base}/products"},
        {"method": "post", "request_url": "${var.base}/cart",
         "json": {"product_id": 1}}
      ]
    }

舊式 ``{"get": {...}}`` map 與裸列表也仍可用，runner 會 normalise 成 ``{"mode": "sequence", "tasks": [...]}``。

加權挑選
--------

每個 task 可帶正整數 ``weight``；runner 每 tick 挑一個，機率與 weight 成正比。未提供 ``weight`` 預設 1。

.. code-block:: json

    {
      "mode": "weighted",
      "tasks": [
        {"method": "get", "request_url": "/", "weight": 3},
        {"method": "get", "request_url": "/expensive", "weight": 1}
      ]
    }

條件流程
--------

``run_if`` 與 ``skip_if`` 皆使用相同預測式語言；``run_if`` 必須為真才執行該 task，``skip_if`` 必須為假才執行。

預測式
~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 形式
     - 意義
   * - ``true`` / ``false`` / int
     - 直接 truthy 檢查。
   * - ``"${var.x}"``
     - 解析占位符後 truthy 檢查。
   * - ``{"equals": [a, b]}``
     - 解析後 ``a == b``。
   * - ``{"not_equals": [a, b]}``
     - 解析後 ``a != b``。
   * - ``{"in": [needle, haystack]}``
     - ``needle in haystack``。
   * - ``{"truthy": value}``
     - 解析後 truthy 檢查。

範例
~~~~

.. code-block:: json

    {
      "mode": "sequence",
      "tasks": [
        {"method": "post", "request_url": "/login",
         "json": {"email": "${var.email}"},
         "extract": [{"var": "auth", "from": "json_path", "path": "token"}]},
        {"method": "get",  "request_url": "/profile",
         "headers": {"Authorization": "Bearer ${var.auth}"},
         "run_if": {"truthy": "${var.auth}"}},
        {"method": "post", "request_url": "/cart",
         "json": {"product_id": 1},
         "skip_if": {"equals": ["${var.tenant}", "internal"]}}
      ]
    }
