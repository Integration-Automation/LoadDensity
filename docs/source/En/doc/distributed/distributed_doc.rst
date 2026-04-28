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

The master waits up to 60 s for ``expected_workers`` workers to join
before starting the load ramp. If only N workers (N < expected) join,
it logs a warning and starts anyway.

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
