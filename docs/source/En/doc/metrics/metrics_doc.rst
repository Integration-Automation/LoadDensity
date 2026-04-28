Metrics Exporters
=================

Overview
--------

LoadDensity ships three observability sinks that hook into Locust's
``request`` event and emit per-request metrics. All three are loaded
lazily and ship as optional extras.

Prometheus
----------

Install: ``pip install je_load_density[prometheus]``.

.. code-block:: python

    from je_load_density import start_prometheus_exporter
    start_prometheus_exporter(port=9646, addr="127.0.0.1")

Metrics:

* ``loaddensity_requests_total{request_type, name, outcome}`` — counter
* ``loaddensity_request_latency_ms{request_type, name}`` — histogram
* ``loaddensity_response_bytes{request_type, name}`` — histogram

The default bind address is loopback. Pass ``addr="0.0.0.0"`` to expose
the endpoint to a Docker / Kubernetes scrape target.

InfluxDB
--------

Stdlib only — no extra package needed. Pick UDP for fire-and-forget or
HTTP for an authenticated cloud endpoint.

.. code-block:: python

    from je_load_density import start_influxdb_sink

    # UDP listener on the InfluxDB box
    start_influxdb_sink(transport="udp", host="127.0.0.1", port=8089)

    # HTTPS write API
    start_influxdb_sink(
        transport="http",
        url="https://eu-central-1-1.aws.cloud2.influxdata.com/api/v2/write?org=...&bucket=...",
        token="...",
    )

The HTTP transport rejects URLs that aren't ``http://`` or ``https://``.

OpenTelemetry
-------------

Install: ``pip install je_load_density[opentelemetry]``.

.. code-block:: python

    from je_load_density import start_opentelemetry_exporter
    start_opentelemetry_exporter(
        endpoint="http://otel-collector:4317",
        service_name="loaddensity",
        export_interval_ms=5000,
    )

Instruments emitted:

* ``loaddensity.requests`` — counter
* ``loaddensity.request.latency`` — histogram (ms)
* ``loaddensity.response.size`` — histogram (bytes)

Each instrument carries ``request_type``, ``name``, and ``outcome``
attributes.

Stop helpers
------------

Each ``start_*`` has a paired ``stop_*`` that detaches the listener
(and shuts down the OTel provider). The Prometheus HTTP server itself
keeps running because ``prometheus_client`` does not expose a stop
hook.

Action JSON
-----------

The same exporters are reachable from action JSON:

.. code-block:: json

    {"load_density": [
      ["LD_start_prometheus_exporter", {"port": 9646, "addr": "127.0.0.1"}],
      ["LD_start_test", {...}],
      ["LD_stop_prometheus_exporter", {}]
    ]}
