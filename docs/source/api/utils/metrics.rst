Metrics Exporters API
=====================

Three exporters ship under ``je_load_density.utils.metrics``: a
Prometheus HTTP endpoint, an InfluxDB line-protocol UDP/HTTP sink, and
an OpenTelemetry OTLP gRPC exporter. All three are lazy-imported and
gated by the matching install extra.

Prometheus
----------

.. code-block:: python

    from je_load_density import start_prometheus_exporter, stop_prometheus_exporter

    start_prometheus_exporter(port=9646, addr="127.0.0.1")
    stop_prometheus_exporter()

Install with ``pip install "je_load_density[prometheus]"`` (or
``[metrics]``).

Exposed metrics:

* ``loaddensity_requests_total{method, name, outcome}``
* ``loaddensity_request_latency_ms{method, name}``
* ``loaddensity_response_bytes{method, name}``

InfluxDB
--------

.. code-block:: python

    from je_load_density import start_influxdb_sink, stop_influxdb_sink

    start_influxdb_sink(transport="udp", host="influxdb", port=8089)
    start_influxdb_sink(transport="http", host="influxdb", port=8086,
                        database="loadtests", username="admin",
                        password="rotate-me")
    stop_influxdb_sink()

Emits a ``loaddensity_request`` measurement carrying ``status_code``,
``method``, ``name``, ``response_time_ms``, ``response_length``, and
the ``outcome`` tag.

Datadog DogStatsD
-----------------

.. code-block:: python

    from je_load_density import start_statsd_sink, stop_statsd_sink

    start_statsd_sink(host="dogstatsd", port=8125, prefix="loaddensity")
    stop_statsd_sink()

Pure UDP, no SDK dependency. Each completed request emits three packets:

* ``<prefix>.requests:1|c|#method:GET,name:/x,outcome:success``
* ``<prefix>.request.latency:42|ms|#method:GET,name:/x,outcome:success``
* ``<prefix>.response.size:1024|h|#method:GET,name:/x,outcome:success``

Tag values are sanitised — pipe / comma / colon / hash characters in
``name`` are replaced with ``_`` so the packet remains parseable.

OpenTelemetry
-------------

.. code-block:: python

    from je_load_density import (
        start_opentelemetry_exporter,
        stop_opentelemetry_exporter,
    )

    start_opentelemetry_exporter(
        endpoint="http://otel-collector:4317",
        service_name="loaddensity",
    )
    stop_opentelemetry_exporter()

Install with ``pip install "je_load_density[opentelemetry]"`` (or
``[metrics]``).

Instruments:

* ``loaddensity.requests`` (counter)
* ``loaddensity.request.latency`` (histogram, milliseconds)
* ``loaddensity.response.size`` (histogram, bytes)

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Command
     - Toggles
   * - ``LD_start_prometheus_exporter`` / ``LD_stop_prometheus_exporter``
     - Prometheus HTTP endpoint.
   * - ``LD_start_influxdb_sink`` / ``LD_stop_influxdb_sink``
     - InfluxDB UDP / HTTP sink.
   * - ``LD_start_opentelemetry_exporter`` / ``LD_stop_opentelemetry_exporter``
     - OTLP gRPC exporter.
   * - ``LD_start_statsd_sink`` / ``LD_stop_statsd_sink``
     - Datadog DogStatsD UDP sink.
