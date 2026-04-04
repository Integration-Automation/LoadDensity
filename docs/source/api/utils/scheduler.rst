Scheduler API
=============

The ``SchedulerManager`` class wraps APScheduler to provide both blocking and non-blocking
job scheduling.

SchedulerManager Class
----------------------

Scheduler Control
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Method
     - Description
   * - ``start_block_scheduler()``
     - Start the blocking scheduler (blocks current thread)
   * - ``start_nonblocking_scheduler()``
     - Start the background scheduler (non-blocking)
   * - ``start_all_scheduler()``
     - Start both blocking and non-blocking schedulers
   * - ``get_blocking_scheduler()``
     - Returns the ``BlockingScheduler`` instance
   * - ``get_nonblocking_scheduler()``
     - Returns the ``BackgroundScheduler`` instance
   * - ``shutdown_blocking_scheduler(wait=False)``
     - Shutdown the blocking scheduler
   * - ``shutdown_nonblocking_scheduler(wait=False)``
     - Shutdown the non-blocking scheduler

Interval Methods (Blocking)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def add_interval_blocking_secondly(
        self, function: Callable, id: str = None,
        args: Union[list, tuple] = None, kwargs: dict = None,
        seconds: int = 1, **trigger_args
    ) -> Job

    def add_interval_blocking_minutely(self, function, id=None, args=None, kwargs=None, minutes=1, **trigger_args) -> Job
    def add_interval_blocking_hourly(self, function, id=None, args=None, kwargs=None, hours=1, **trigger_args) -> Job
    def add_interval_blocking_daily(self, function, id=None, args=None, kwargs=None, days=1, **trigger_args) -> Job
    def add_interval_blocking_weekly(self, function, id=None, args=None, kwargs=None, weeks=1, **trigger_args) -> Job

**Common Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Type
     - Description
   * - ``function``
     - ``Callable``
     - Function to execute on schedule
   * - ``id``
     - ``str``
     - Unique job identifier (for later removal)
   * - ``args``
     - ``list`` or ``tuple``
     - Positional arguments for the function
   * - ``kwargs``
     - ``dict``
     - Keyword arguments for the function
   * - ``seconds/minutes/hours/days/weeks``
     - ``int``
     - Interval duration

**Returns:** ``Job`` — APScheduler Job instance.

Interval Methods (Non-blocking)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def add_interval_nonblocking_secondly(self, function, id=None, args=None, kwargs=None, seconds=1, **trigger_args) -> Job
    def add_interval_nonblocking_minutely(self, function, id=None, args=None, kwargs=None, minutes=1, **trigger_args) -> Job
    def add_interval_nonblocking_hourly(self, function, id=None, args=None, kwargs=None, hours=1, **trigger_args) -> Job
    def add_interval_nonblocking_daily(self, function, id=None, args=None, kwargs=None, days=1, **trigger_args) -> Job
    def add_interval_nonblocking_weekly(self, function, id=None, args=None, kwargs=None, weeks=1, **trigger_args) -> Job

Same parameters as blocking variants, but jobs are scheduled on the background scheduler.

Cron Methods
~~~~~~~~~~~~

.. code-block:: python

    def add_cron_blocking(self, function: Callable, id: str = None, **trigger_args) -> Job
    def add_cron_nonblocking(self, function: Callable, id: str = None, **trigger_args) -> Job

Add cron-style scheduled jobs. Pass cron arguments via ``**trigger_args``.

Job Management
~~~~~~~~~~~~~~

.. code-block:: python

    def remove_blocking_job(self, id: str, jobstore: str = 'default') -> Any
    def remove_nonblocking_job(self, id: str, jobstore: str = 'default') -> Any

Remove a job by its ID from the specified jobstore.

Low-level Job Methods
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def add_blocking_job(
        self, func: Callable, trigger=None, args=None, kwargs=None,
        id=None, name=None, misfire_grace_time=undefined,
        coalesce=undefined, max_instances=undefined,
        next_run_time=undefined, jobstore='default',
        executor='default', replace_existing=False,
        **trigger_args
    ) -> Job

    def add_nonblocking_job(
        self, func: Callable, trigger=None, args=None, kwargs=None,
        id=None, name=None, misfire_grace_time=undefined,
        coalesce=undefined, max_instances=undefined,
        next_run_time=undefined, jobstore='default',
        executor='default', replace_existing=False,
        **trigger_args
    ) -> Job

Direct wrappers around APScheduler's ``add_job()`` method, providing full control over
job configuration.
