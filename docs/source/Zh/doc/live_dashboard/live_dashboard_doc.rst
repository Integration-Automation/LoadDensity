即時 Dashboard
==============

概觀
----

stdlib-only HTTP server,搭配 Server-Sent Events 串流即時把
``test_record_instance`` 的統計推送到瀏覽器。適合 demo、戰情室、on-call。

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Endpoint
     - 回傳
   * - ``GET /``
     - 單頁 HTML(即時 tile + per-name 表格)
   * - ``GET /events``
     - ``text/event-stream``,每個 refresh 間隔一筆 JSON snapshot
   * - ``GET /snapshot``
     - 一次性 JSON,給 polling client 使用

啟動 / 停止
-----------

.. code-block:: python

    from je_load_density import start_dashboard, stop_dashboard

    start_dashboard(
        host="127.0.0.1", port=8765,
        refresh_seconds=1.0, window_seconds=10.0,
    )
    # ... 跑 action ...
    stop_dashboard()

Snapshot payload 範例:

.. code-block:: json

    {
      "totals": {"requests": 1234, "failures": 7, "failure_rate": 0.0057},
      "latency_overall": {"p50_ms": 42, "p95_ms": 180},
      "per_name": {"/checkout": {"count": 200, "p95_ms": 220}},
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
