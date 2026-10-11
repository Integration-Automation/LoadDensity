Distributed Master / Worker
===========================

Overview
--------

LoadDensity exposes Locust's distributed runner via a ``runner_mode``
parameter on ``start_test`` / ``prepare_env``. Three modes are
supported:

* ``local`` — single process (default).
* ``master`` — coordinates a cluster of workers, optionally serves the
  Locust Web UI.
* ``worker`` — joins a master and runs the requested user count.

Master
------

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="master",
        master_bind_host="0.0.0.0",
        master_bind_port=5557,
        expected_workers=4,                # wait for 4 workers
        web_ui_dict={"host": "0.0.0.0", "port": 8089},
        user_count=400,
        spawn_rate=40,
        test_time=600,
        tasks=[...],
    )

The master waits for healthy ready workers. Configure ``worker_startup_timeout``
(default 60 s), ``worker_heartbeat_interval`` (5 s), ``worker_lost_timeout`` (15 s)
and ``worker_startup_policy`` (``"fail"``). An unmet count raises ``TimeoutError``
after cleanup. Explicit ``"degraded"`` policy permits a shortfall but requires at
least one ready worker, including when ``expected_workers=0``.

All nodes must use matching heartbeat settings; native detection follows interval
ticks. Locust rebalances virtual-user capacity after loss/reconnection and all
workers lost terminates the run. Master results include ``distributed_health``,
observed capacity and affected IDs. Stateful journeys may restart; requests are
not replayed. Finite-work leases and canonical worker-record aggregation remain pending.

``on_environment(env)`` runs before startup in the execution thread;
``stop_requested()`` cooperatively cancels startup, ramp-up or execution. Callback
errors propagate after cleanup. ``prepare_env`` owns runner/UI/RPC/auxiliary tasks;
direct ``create_env`` callers must call ``cleanup_env(env)`` when finished.

Worker
------

Run on each load-generating node:

.. code-block:: python

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        runner_mode="worker",
        master_host="10.0.0.10",
        master_port=5557,
        tasks=[...],
    )

Workers do not start a Web UI and skip the local stats greenlets — the
master collects and publishes aggregate stats.

Tips
----

* Open the master ``master_bind_port`` in your firewall. Default
  Locust port is ``5557``.
* Use ``master_bind_host="0.0.0.0"`` only when the master is reachable
  by the workers; bind to a private interface IP otherwise.
* Match the user template (``http_user`` / ``fast_http_user`` / ...)
  on master and workers — the master broadcasts the user class name.
* If you parameterise tasks with ``${csv.X.col}``, register the same
  CSV files on every worker (they don't share state).

Cloud launch contracts
----------------------

Cloud adapters validate worker/resource settings before contacting providers.
``je_load_density.cloud.CloudLaunchError`` preserves prior accepted responses,
failed worker indices and failed response details; provider exceptions remain chained.
Fargate rejects partial and malformed submissions. Lambda distinguishes successful
execution from Event acceptance and DryRun validation, retains FunctionError payloads,
and closes payload streams. ACI waits for provisioning and returns unique ``name``,
``status="Succeeded"`` and ``resource_id``. Cloud Run refreshes credentials per call;
configure parallelism on the deployed Job, since per-run overrides accept
``task_count`` and reject ``parallelism``. Launchers do not retry or roll back launches.

Mandatory contract tests use controlled SDK doubles and local HTTP. Optional cloud
extra tests also verify official SDK serialization/stubs; they create no resources.
Accepted launch responses do not prove worker readiness or successful load completion.
