Live Dashboard API
==================

stdlib HTTP + Server-Sent Events server that streams the running stats
from ``test_record_instance``.

start_dashboard()
-----------------

.. code-block:: python

    from je_load_density import start_dashboard, stop_dashboard

    start_dashboard(
        host="127.0.0.1",
        port=8765,
        refresh_seconds=1.0,
        window_seconds=10.0,
    )

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Default
     - Description
   * - ``host``
     - ``"127.0.0.1"``
     - Bind address.
   * - ``port``
     - ``8765``
     - Bind port.
   * - ``refresh_seconds``
     - ``1.0``
     - SSE push interval.
   * - ``window_seconds``
     - ``10.0``
     - Sliding window for ``rps`` / ``avg_ms`` calculation.

**Returns:** ``LiveDashboardServer``.

stop_dashboard()
----------------

Cleanly shuts down the running server (idempotent).

snapshot_metrics()
------------------

.. code-block:: python

    from je_load_density import snapshot_metrics

    payload = snapshot_metrics(window_seconds=10.0)

Returns the dict served by ``/snapshot``:

* ``totals``         — overall counts (re-used from ``build_summary``)
* ``latency_overall``— overall percentiles
* ``per_name``       — per-endpoint stats
* ``rps``            — rolling RPS over ``window_seconds``
* ``avg_ms``         — rolling mean latency
* ``ts``             — Unix time of the snapshot

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - URL
     - Returns
   * - ``GET /``
     - Single-page HTML.
   * - ``GET /events``
     - ``text/event-stream`` (one snapshot per ``refresh_seconds``).
   * - ``GET /snapshot``
     - One-shot JSON.

Action-JSON commands
--------------------

* ``LD_start_dashboard`` / ``LD_stop_dashboard``
