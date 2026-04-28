斷言與擷取
==========

概觀
----

HTTP / FastHttp task 可附 ``assertions`` 與 ``extract``，會在 Locust 的 ``catch_response`` 之下執行。失敗的斷言會被 Locust 標為 failure，並出現在所有報告中。

斷言
----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``type``
     - 行為
   * - ``status_code``
     - ``int(response.status_code) == int(value)``。
   * - ``contains``
     - ``str(value) in response.text``。
   * - ``not_contains``
     - ``str(value) not in response.text``。
   * - ``json_path``
     - 沿著 ``path``（點分隔，支援 list 索引）解析 ``response.json()`` 後與 ``value`` 比對。
   * - ``header``
     - ``response.headers[name] == value``。

範例
~~~~

.. code-block:: json

    {
      "method": "get",
      "request_url": "${var.base}/health",
      "assertions": [
        {"type": "status_code", "value": 200},
        {"type": "json_path", "path": "status", "value": "ok"},
        {"type": "header", "name": "X-Service", "value": "checkout"}
      ]
    }

擷取
----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``from``
     - 來源
   * - ``json_path``
     - 與 ``json_path`` 斷言相同的點分語法。
   * - ``header``
     - ``response.headers[name]``。
   * - ``status_code``
     - ``response.status_code``。

擷取值會以指定 ``var`` 名寫入參數解析器；後續 task 以 ``${var.NAME}`` 引用。
