start_test & prepare_env
========================

Overview
--------

``start_test`` is the high-level entrypoint that picks a user template,
seeds the parameter resolver, and asks ``prepare_env`` to build a Locust
environment in the requested mode (local / master / worker).

Signature
---------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=60,
        web_ui_dict=None,                  # {"host": "...", "port": ...}
        runner_mode="local",               # "local" | "master" | "worker"
        master_bind_host="*",
        master_bind_port=5557,
        master_host="127.0.0.1",
        master_port=5557,
        expected_workers=0,
        tasks=...,
        variables={"host": "https://api.example.com"},
        csv_sources=[{"name": "users", "file_path": "users.csv"}],
    )

Supported user types
--------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - ``user``
     - Template
   * - ``http_user``
     - ``locust.HttpUser`` wrapper backed by ``requests``.
   * - ``fast_http_user``
     - ``locust.FastHttpUser`` wrapper backed by ``geventhttpclient``.
   * - ``websocket_user``
     - WebSocket frame loop (lazy ``websocket-client`` import).
   * - ``grpc_user``
     - Unary gRPC calls against operator-supplied stubs.
   * - ``mqtt_user``
     - MQTT publish / subscribe loop.
   * - ``socket_user``
     - Raw TCP / UDP send-recv.

prepare_env
-----------

``prepare_env`` is the lower-level layer behind ``start_test``. It is
useful when you want to build a Locust environment manually, for
example to integrate with another runner.

.. code-block:: python

    from je_load_density import prepare_env
    from je_load_density.wrapper.user_template.fast_http_user_template import (
        FastHttpUserWrapper, set_wrapper_fasthttp_user,
    )

    set_wrapper_fasthttp_user(
        {"user": "fast_http_user"},
        tasks=[{"method": "get", "request_url": "https://example.com/"}],
    )
    prepare_env(
        user_class=FastHttpUserWrapper,
        user_count=50,
        spawn_rate=10,
        test_time=60,
        runner_mode="local",
    )

Distributed mode
----------------

Master::

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="master",
        master_bind_host="0.0.0.0",
        master_bind_port=5557,
        expected_workers=4,
        user_count=200,
        spawn_rate=20,
        test_time=300,
        tasks=[...],
    )

Worker (run on each node, on the same network as master)::

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="worker",
        master_host="10.0.0.10",
        master_port=5557,
        tasks=[...],
    )

The master waits for ``expected_workers`` workers to register before
ramping up. Workers join the master and run the requested user count
proportional to the cluster size.

Native asyncio HTTP
-------------------

Pass ``engine="asyncio"`` to the public ``start_test`` or ``LD_start_test``.
The default stays ``locust``. In an active event loop, use
``await run_async_load(tasks, users, duration_seconds, ...)`` instead.
Package/native imports do not load Locust or patch process I/O.
After selecting Locust, use a fresh interpreter for native I/O; CLI bench and
the desktop supervisor provide this isolation.

Native HTTP supports request parameters/body/headers/cookies/auth/redirects,
all five HTTP assertions and three extractor kinds, independent user sessions,
sequence/weighted/conditional scenarios, retry, asynchronous think time/token
buckets, ramp and stages/spike/soak shapes. Client TLS/proxy settings are reused
per user. Certificates never modify another user's trust context. If supplying
an SSLContext, configure its certificate directly and omit cert/client_cert.
Malformed or unsupported options are rejected before requests; protocols other
than HTTP and master/worker modes remain unsupported. Metrics exporter parity
is still outstanding.

``AsyncRunHandle`` exposes awaitable ``start``/``wait`` and ``stop``/``snapshot``.
``stop_requested`` and ``on_environment`` callbacks work with both engines.
Cancellation closes owned tasks and clients, while unexpected worker/cleanup
errors propagate. Each result includes an isolated ``summary`` suitable for
SLA evaluation. Legacy report lists and optional canonical RunContext recording
remain compatible. ``requests`` counts successes; ``summary.totals.requests``
counts all measured attempts. HTTP 4xx/5xx fail unless a passing status-code
assertion explicitly expects that status. Native durations/counts/rates must be
positive finite numbers; counts must be integral.

Canonical distributed results
-----------------------------

The opt-in master passes ``run_context=DistributedRunContext()`` imported from
``je_load_density.utils.test_record.distributed_context``. Every worker enables
``distributed_records=True``. This requires the coordinated ActionCore record
API; legacy-only environments retain their published dependency floor.
Master ingestion preserves worker identity, validates the whole batch before
mutation and globally deduplicates record IDs. Newly accepted records populate
legacy reports once. Inspect ``env.record_delivery.snapshot()`` for diagnostics.

Default limits are 100 records/262144 bytes per batch, 65536 bytes per record,
1000 records/4194304 queued bytes, 0.1-second retries and 2-second drain/terminal
acknowledgement budgets. Configure with ``record_batch_size``,
``record_batch_bytes``, ``record_max_bytes``, ``record_max_pending``,
``record_pending_bytes``, ``record_flush_interval`` and ``record_drain_timeout``.
Queue overflow, conflicting retries and incomplete final delivery fail explicitly.
Storage is in memory until exported. Native ongoing-user rebalancing does not
replay requests, migrate sessions or supply finite shards/exactly-once execution.
