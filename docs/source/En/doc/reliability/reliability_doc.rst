Reliability
===========

Overview
--------

Four reliability controls let LoadDensity run unattended in CI without
turning into a flake factory:

* **Adaptive retry** — exponential backoff + jitter + per-error-class
  budgets, so transient flakes recover while real bugs surface
  immediately.
* **Failure budget / circuit breaker** — sliding-window error rate;
  the run aborts itself if a regression starts cascading.
* **Network conditioner** — inject latency / jitter / loss per task
  without kernel ``tc`` or external proxies.
* **Process supervisor** — kill orphan Locust / gevent workers and
  enforce a hard wall-clock timeout on any callable.

Each control is independently optional. They all live under
``je_load_density.utils.reliability``.

Adaptive retry
--------------

``classify_error`` buckets an exception into one of three categories:

* ``transient`` — connection failures, timeouts, remote disconnects
  (default budget: 5).
* ``flaky`` — ``AssertionError``, ``JSONDecodeError`` (default
  budget: 2).
* ``permanent`` — everything else (budget: 0, raised immediately).

.. code-block:: python

    from je_load_density import AdaptiveRetryPolicy, run_with_retry

    policy = AdaptiveRetryPolicy(
        transient_budget=5, flaky_budget=2,
        base_delay=0.1, max_delay=2.0,
        backoff_factor=2.0, jitter=0.25,
    )
    run_with_retry(lambda: do_request(), policy=policy)

Per-task declaration inside an action JSON:

.. code-block:: json

    {"method": "post", "request_url": "${var.base}/x",
     "retry": {"transient": 3, "flaky": 1, "base_delay": 0.2}}

Failure budget
--------------

.. code-block:: python

    from je_load_density import install_failure_budget

    budget = install_failure_budget(
        threshold=0.05,        # >5% errors
        window_seconds=30,     # …in the last 30s
        min_samples=50,        # …once at least 50 requests have run
        runner_quit_callback=lambda: env.runner.quit(),
    )

Tripping fires the ``runner_quit_callback`` once; subsequent failures
are ignored. ``current_budget()`` returns the active sub-system for
inspection.

Network conditioner
-------------------

Inject latency / jitter / packet loss per task. Drops are simulated by
raising a ``ConnectionError`` before the request fires (so retry
budgets see them as transient).

.. code-block:: python

    from je_load_density import install_network_conditioner

    install_network_conditioner(
        latency_ms=50,
        jitter_ms=20,
        loss_rate=0.01,
        name_filter="/checkout",   # only this endpoint
    )

Process supervisor
------------------

.. code-block:: python

    from je_load_density import ProcessSupervisor, with_watchdog

    # Kill orphan Locust / gevent processes (psutil soft-dep)
    killed_pids = ProcessSupervisor().kill_orphans()

    # Hard wall-clock raise after N seconds
    result = with_watchdog(
        lambda: execute_action(action_json),
        timeout_seconds=600,
        on_timeout=lambda: print("dumping state…"),
    )

The watchdog runs the callable in a daemon thread; on timeout it
raises :class:`TimeoutError` on the caller and leaves the thread to
the process exit.

Action JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Summary
   * - ``LD_install_failure_budget``
     - Subscribe to Locust request events with a sliding-window budget.
   * - ``LD_uninstall_failure_budget``
     - Detach the budget listener.
   * - ``LD_install_network_conditioner``
     - Install global latency / jitter / loss injector.
   * - ``LD_uninstall_network_conditioner``
     - Detach the conditioner.
