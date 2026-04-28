指標 Exporter
=============

概觀
----

LoadDensity 內含三個可觀測性 sink，掛上 Locust 的 ``request`` 事件，逐請求送出指標。三者皆 lazy load，並以選用 extras 提供。

Prometheus
----------

安裝：``pip install je_load_density[prometheus]``。

.. code-block:: python

    from je_load_density import start_prometheus_exporter
    start_prometheus_exporter(port=9646, addr="127.0.0.1")

指標：

* ``loaddensity_requests_total{request_type, name, outcome}`` — counter
* ``loaddensity_request_latency_ms{request_type, name}`` — histogram
* ``loaddensity_response_bytes{request_type, name}`` — histogram

預設僅綁 loopback。要對 Docker / Kubernetes scraping target 開放，請改傳 ``addr="0.0.0.0"``。

InfluxDB
--------

僅用標準函式庫，無需額外套件。可選 UDP（fire-and-forget）或 HTTP（含 token）。

.. code-block:: python

    from je_load_density import start_influxdb_sink

    # InfluxDB UDP listener
    start_influxdb_sink(transport="udp", host="127.0.0.1", port=8089)

    # HTTPS write API
    start_influxdb_sink(
        transport="http",
        url="https://eu-central-1-1.aws.cloud2.influxdata.com/api/v2/write?org=...&bucket=...",
        token="...",
    )

HTTP transport 會拒絕非 ``http://`` / ``https://`` 的 URL。

OpenTelemetry
-------------

安裝：``pip install je_load_density[opentelemetry]``。

.. code-block:: python

    from je_load_density import start_opentelemetry_exporter
    start_opentelemetry_exporter(
        endpoint="http://otel-collector:4317",
        service_name="loaddensity",
        export_interval_ms=5000,
    )

送出的儀器：

* ``loaddensity.requests`` — counter
* ``loaddensity.request.latency`` — histogram（ms）
* ``loaddensity.response.size`` — histogram（bytes）

每個儀器皆攜帶 ``request_type``、``name``、``outcome`` 屬性。

Stop helpers
------------

每個 ``start_*`` 都有對應的 ``stop_*``，會卸下 listener（並 shutdown OTel provider）。Prometheus HTTP server 因 ``prometheus_client`` 沒提供 stop hook，只能繼續執行。

動作 JSON
---------

.. code-block:: json

    {"load_density": [
      ["LD_start_prometheus_exporter", {"port": 9646, "addr": "127.0.0.1"}],
      ["LD_start_test", {...}],
      ["LD_stop_prometheus_exporter", {}]
    ]}
