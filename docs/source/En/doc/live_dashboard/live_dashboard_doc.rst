Live Dashboard
==============

Overview
--------

A stdlib-only HTTP server with a Server-Sent Events stream that pushes
running stats from ``test_record_instance`` to any browser. Use it for
demos, war rooms, and on-call.

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Endpoint
     - Returns
   * - ``GET /``
     - Single-page HTML with live tiles + per-name table.
   * - ``GET /events``
     - ``text/event-stream``: one JSON snapshot per refresh interval.
   * - ``GET /snapshot``
     - One-shot JSON, suitable for polling clients.

Start / stop
------------

.. code-block:: python

    from je_load_density import start_dashboard, stop_dashboard

    start_dashboard(
        host="127.0.0.1",
        port=8765,
        refresh_seconds=1.0,
        window_seconds=10.0,
    )
    # … run actions …
    stop_dashboard()

The snapshot payload looks like:

.. code-block:: json

    {
      "totals": {"requests": 1234, "failures": 7, "failure_rate": 0.0057, ...},
      "latency_overall": {"p50_ms": 42, "p95_ms": 180, ...},
      "per_name": {"/checkout": {"count": 200, "p95_ms": 220, ...}},
      "rps": 41.3,
      "avg_ms": 51.2,
      "ts": 1748256000.0
    }

Action JSON
-----------

.. code-block:: json

    [["LD_start_dashboard", {"host": "127.0.0.1", "port": 8765}],
     ["LD_start_test", {...}],
     ["LD_stop_dashboard"]]
