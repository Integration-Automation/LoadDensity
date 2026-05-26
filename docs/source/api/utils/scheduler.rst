Scheduler API (removed)
=======================

.. note::

    The bundled ``SchedulerManager`` wrapper around APScheduler has been
    removed from LoadDensity. If you need cron-style scheduling, drive
    LoadDensity from your own scheduler:

    * ``APScheduler`` directly (``pip install apscheduler``).
    * ``cron`` / Windows Task Scheduler calling
      ``python -m je_load_density run <file>``.
    * GitHub Actions / GitLab CI cron triggers.

    The :doc:`socket_server` API is the recommended remote-control
    surface; pair it with any external scheduler for cron-driven runs.
