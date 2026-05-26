匯入器
======

概觀
----

六個匯入器把現實世界的壓測資產轉成 LoadDensity action JSON 或單一
task dict。產出的 task schema 完全一致,因此下游 ``LD_start_test``
payload 與輸入格式無關。

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - 來源
     - LoadDensity helper
   * - HAR(瀏覽器 DevTools、mitmproxy、Charles…)
     - ``load_har`` + ``har_to_tasks`` / ``har_to_action_json``
   * - Postman v2.1 collection
     - ``load_postman_collection`` + ``postman_to_*``
   * - OpenAPI 3.x(JSON / YAML)
     - ``load_openapi`` + ``openapi_to_*``
   * - 單一 cURL 指令
     - ``curl_to_task``
   * - k6 腳本(``http.get/post/...``、``check()``)
     - ``load_k6_script`` + ``k6_script_to_*``
   * - JMeter JMX
     - ``load_jmeter_jmx`` + ``jmeter_to_*``

cURL
----

.. code-block:: python

    from je_load_density import curl_to_task

    task = curl_to_task("""curl -X POST https://api/login \\
        -H 'Content-Type: application/json' \\
        -d '{"email":"u@x","password":"s"}'""")

支援旗標:``-X / --request``、``-H / --header``、
``-d / --data / --data-raw / --data-binary / --data-urlencode``、
``-u / --user``(basic auth)、``-b / --cookie``、
``-k / --insecure``、``-L / --location``、``--compressed``。

HAR
---

.. code-block:: python

    from je_load_density import load_har, har_to_action_json

    action_json = har_to_action_json(
        load_har("recording.har"),
        user="fast_http_user",
        user_count=20, spawn_rate=10, test_time=120,
        include=[r"api\.example\.com"],
        exclude=[r"\.svg$"],
    )

HAR 內回應狀態碼會自動成為每個 task 的 ``status_code`` 斷言。

Postman v2.1
------------

.. code-block:: python

    from je_load_density import (
        load_postman_collection,
        postman_to_action_json,
    )

    action_json = postman_to_action_json(
        load_postman_collection("collection.json"),
        user="fast_http_user", user_count=20, spawn_rate=10, test_time=120,
    )

遞迴走訪 folder;raw / urlencoded / formdata body 皆支援;disabled
header / field 自動跳過。

OpenAPI 3.x
-----------

.. code-block:: python

    from je_load_density import load_openapi, openapi_to_action_json

    action_json = openapi_to_action_json(
        load_openapi("openapi.yaml"),    # YAML 需 [yaml] extra
        user="fast_http_user", user_count=20, spawn_rate=10, test_time=120,
    )

每個 ``(path, method)`` 變成一個 task;``{param}`` 路徑參數會被改寫為
``${var.param}``,供呼叫者透過 ``register_variables`` 提供值。第一個
2xx 回應狀態碼會成為 ``status_code`` 斷言。

k6
--

.. code-block:: python

    from je_load_density import load_k6_script, k6_script_to_action_json

    action_json = k6_script_to_action_json(load_k6_script("script.js"))

實用主義解析器 — 抓 ``http.<method>(...)`` 呼叫以及相鄰的
``check(res, {...})``。不是完整 ES module 評估器;設計用於一次性遷移,
不追求 1:1 來回轉換。

JMeter JMX
----------

.. code-block:: python

    from je_load_density import load_jmeter_jmx, jmeter_to_action_json

    action_json = jmeter_to_action_json(load_jmeter_jmx("plan.jmx"))

走訪 XML,為每個 ``HTTPSamplerProxy`` 產生一個 task,並繼承外層
``HeaderManager`` 設定;form ``Arguments`` 轉成 body 字串或 dict。

Action JSON 指令
----------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 指令
     - 說明
   * - ``LD_load_har`` / ``LD_har_to_tasks`` / ``LD_har_to_action_json``
     - HAR pipeline
   * - ``LD_load_postman_collection`` / ``LD_postman_to_*``
     - Postman pipeline
   * - ``LD_load_openapi`` / ``LD_openapi_to_*``
     - OpenAPI pipeline
   * - ``LD_curl_to_task``
     - 解析一條 cURL
   * - ``LD_load_k6_script`` / ``LD_k6_script_to_*``
     - k6 pipeline
   * - ``LD_load_jmeter_jmx`` / ``LD_jmeter_to_*``
     - JMeter JMX pipeline
