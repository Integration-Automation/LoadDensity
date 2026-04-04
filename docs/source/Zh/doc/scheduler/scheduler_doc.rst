排程器
======

LoadDensity 內建排程器，可讓您在指定的時間間隔排程重複執行測試。
排程器支援阻塞（blocking）與非阻塞（non-blocking）兩種模式。

基本用法
--------

.. code-block:: python

    from je_load_density.utils.scheduler.scheduler_manager import SchedulerManager

    scheduler = SchedulerManager()

    def my_task():
        print("排程任務已執行")

    # 新增每 5 秒執行一次的工作（阻塞模式）
    scheduler.add_interval_blocking_secondly(my_task, seconds=5)

    # 啟動阻塞排程器
    scheduler.start_block_scheduler()

阻塞 vs 非阻塞
----------------

排程器有兩種模式：

* **阻塞模式** — ``start_block_scheduler()`` 會阻塞當前執行緒。適用於獨立的排程腳本。
* **非阻塞模式** — ``start_nonblocking_scheduler()`` 在背景執行緒中執行排程器。
  適用於需要繼續執行其他程式碼的情境。

間隔方法（阻塞）
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - 方法
     - 說明
   * - ``add_interval_blocking_secondly(func, seconds)``
     - 每 N 秒執行一次
   * - ``add_interval_blocking_minutely(func, minutes)``
     - 每 N 分鐘執行一次
   * - ``add_interval_blocking_hourly(func, hours)``
     - 每 N 小時執行一次
   * - ``add_interval_blocking_daily(func, days)``
     - 每 N 天執行一次
   * - ``add_interval_blocking_weekly(func, weeks)``
     - 每 N 週執行一次

間隔方法（非阻塞）
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - 方法
     - 說明
   * - ``add_interval_nonblocking_secondly(func, seconds)``
     - 每 N 秒執行一次（非阻塞）
   * - ``add_interval_nonblocking_minutely(func, minutes)``
     - 每 N 分鐘執行一次（非阻塞）
   * - ``add_interval_nonblocking_hourly(func, hours)``
     - 每 N 小時執行一次（非阻塞）
   * - ``add_interval_nonblocking_daily(func, days)``
     - 每 N 天執行一次（非阻塞）
   * - ``add_interval_nonblocking_weekly(func, weeks)``
     - 每 N 週執行一次（非阻塞）

Cron 方法
---------

用於類似 cron 的排程：

* ``add_cron_blocking(func, **cron_args)`` — 以阻塞模式新增 cron 工作
* ``add_cron_nonblocking(func, **cron_args)`` — 以非阻塞模式新增 cron 工作

工作管理
--------

* ``remove_blocking_job(job_id)`` — 從阻塞排程器移除工作
* ``remove_nonblocking_job(job_id)`` — 從非阻塞排程器移除工作

啟動排程器
----------

* ``start_block_scheduler()`` — 啟動阻塞排程器（阻塞當前執行緒）
* ``start_nonblocking_scheduler()`` — 啟動非阻塞排程器（背景執行）
* ``start_all_scheduler()`` — 啟動兩種排程器

範例：排程負載測試
-------------------

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

    # 每 60 秒執行一次測試
    scheduler.add_interval_blocking_secondly(run_test, seconds=60)
    scheduler.start_block_scheduler()
