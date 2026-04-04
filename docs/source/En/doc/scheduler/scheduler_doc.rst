Scheduler
=========

LoadDensity includes a built-in scheduler that allows you to schedule recurring test
execution at defined intervals. The scheduler supports both blocking and non-blocking modes.

Basic Usage
-----------

.. code-block:: python

    from je_load_density.utils.scheduler.scheduler_manager import SchedulerManager

    scheduler = SchedulerManager()

    def my_task():
        print("Scheduled task executed")

    # Add a job that runs every 5 seconds (blocking mode)
    scheduler.add_interval_blocking_secondly(my_task, seconds=5)

    # Start the blocking scheduler
    scheduler.start_block_scheduler()

Blocking vs Non-blocking
-------------------------

The scheduler has two modes:

* **Blocking mode** — ``start_block_scheduler()`` blocks the current thread. Use this for
  standalone scheduler scripts.
* **Non-blocking mode** — ``start_nonblocking_scheduler()`` runs the scheduler in a background
  thread. Use this when you need to continue executing other code.

Interval Methods (Blocking)
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Method
     - Description
   * - ``add_interval_blocking_secondly(func, seconds)``
     - Run every N seconds
   * - ``add_interval_blocking_minutely(func, minutes)``
     - Run every N minutes
   * - ``add_interval_blocking_hourly(func, hours)``
     - Run every N hours
   * - ``add_interval_blocking_daily(func, days)``
     - Run every N days
   * - ``add_interval_blocking_weekly(func, weeks)``
     - Run every N weeks

Interval Methods (Non-blocking)
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Method
     - Description
   * - ``add_interval_nonblocking_secondly(func, seconds)``
     - Run every N seconds (non-blocking)
   * - ``add_interval_nonblocking_minutely(func, minutes)``
     - Run every N minutes (non-blocking)
   * - ``add_interval_nonblocking_hourly(func, hours)``
     - Run every N hours (non-blocking)
   * - ``add_interval_nonblocking_daily(func, days)``
     - Run every N days (non-blocking)
   * - ``add_interval_nonblocking_weekly(func, weeks)``
     - Run every N weeks (non-blocking)

Cron Methods
------------

For cron-like scheduling:

* ``add_cron_blocking(func, **cron_args)`` — Add a cron job in blocking mode
* ``add_cron_nonblocking(func, **cron_args)`` — Add a cron job in non-blocking mode

Job Management
--------------

* ``remove_blocking_job(job_id)`` — Remove a job from the blocking scheduler
* ``remove_nonblocking_job(job_id)`` — Remove a job from the non-blocking scheduler

Starting Schedulers
-------------------

* ``start_block_scheduler()`` — Start the blocking scheduler (blocks current thread)
* ``start_nonblocking_scheduler()`` — Start the non-blocking scheduler (background)
* ``start_all_scheduler()`` — Start both schedulers

Example: Scheduled Load Test
-----------------------------

.. code-block:: python

    from je_load_density import start_test
    from je_load_density.utils.scheduler.scheduler_manager import SchedulerManager

    scheduler = SchedulerManager()

    def run_test():
        start_test(
            user_detail_dict={"user": "fast_http_user"},
            user_count=10,
            spawn_rate=5,
            test_time=5,
            tasks={"get": {"request_url": "http://httpbin.org/get"}},
        )

    # Run the test every 60 seconds
    scheduler.add_interval_blocking_secondly(run_test, seconds=60)
    scheduler.start_block_scheduler()
