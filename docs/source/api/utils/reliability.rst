Reliability API
===============

Four controls let LoadDensity survive unattended CI runs. All live
under ``je_load_density.utils.reliability`` and are re-exported from
the top-level package.

Adaptive retry
--------------

.. code-block:: python

    from je_load_density import (
        AdaptiveRetryPolicy,
        classify_error,
        run_with_retry,
    )

    policy = AdaptiveRetryPolicy(
        transient_budget=5,
        flaky_budget=2,
        permanent_budget=0,
        base_delay=0.1,
        max_delay=5.0,
        backoff_factor=2.0,
        jitter=0.25,
    )
    run_with_retry(lambda: do_request(), policy=policy)

``classify_error(exception)`` returns ``"transient"``, ``"flaky"``,
or ``"permanent"`` based on the exception class name. Replace it via
``AdaptiveRetryPolicy(classifier=...)`` to handle custom exception
types.

Per-task declaration::

    {"method": "post", "request_url": "${var.base}/x",
     "retry": {"transient": 3, "flaky": 1, "base_delay": 0.2}}

Failure budget
--------------

.. code-block:: python

    from je_load_density import (
        FailureBudget,
        CircuitOpenError,
        install_failure_budget,
        uninstall_failure_budget,
    )

    budget = install_failure_budget(
        threshold=0.05,
        window_seconds=30,
        min_samples=50,
        runner_quit_callback=lambda: env.runner.quit(),
    )

* ``FailureBudget.record(failed)`` records one outcome.
* ``FailureBudget.failure_rate()`` computes the current rolling rate.
* ``FailureBudget.is_breached()`` returns ``True`` once
  ``min_samples`` is reached *and* rate > ``threshold``.
* ``CircuitOpenError`` is the exception type users can raise from
  their own ``runner_quit_callback``.

Network conditioner
-------------------

.. code-block:: python

    from je_load_density import (
        NetworkConditioner,
        install_network_conditioner,
        uninstall_network_conditioner,
    )

    install_network_conditioner(
        latency_ms=50,
        jitter_ms=20,
        loss_rate=0.01,
        name_filter="/checkout",
    )

A non-zero ``loss_rate`` raises ``ConnectionError`` before the
request fires, so retry budgets see it as a transient failure.

Process supervisor
------------------

.. code-block:: python

    from je_load_density import ProcessSupervisor, with_watchdog

    killed = ProcessSupervisor().kill_orphans()   # requires psutil

    with_watchdog(
        lambda: execute_action(action_json),
        timeout_seconds=600,
        on_timeout=lambda: print("dumping state…"),
    )

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Summary
   * - ``LD_install_failure_budget`` / ``LD_uninstall_failure_budget``
     - Toggle the sliding-window failure budget listener.
   * - ``LD_install_network_conditioner`` / ``LD_uninstall_network_conditioner``
     - Toggle the latency / jitter / loss injector.
