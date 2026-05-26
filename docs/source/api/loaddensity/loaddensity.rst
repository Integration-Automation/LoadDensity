LoadDensity Core API
====================

The core API provides the entry points for starting load tests,
building Locust environments, accessing the in-memory test record
store, and the proxy used to inject tasks into user templates.

start_test()
------------

The primary function for running a load test.

.. code-block:: python

    def start_test(
        user_detail_dict: Dict[str, Any],
        user_count: int = 50,
        spawn_rate: int = 10,
        test_time: Optional[int] = 60,
        web_ui_dict: Optional[Dict[str, Any]] = None,
        runner_mode: str = "local",
        master_bind_host: str = "*",
        master_bind_port: int = 5557,
        master_host: str = "127.0.0.1",
        master_port: int = 5557,
        expected_workers: int = 0,
        **kwargs,
    ) -> Dict[str, Any]

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 20 15 40

   * - Parameter
     - Type
     - Default
     - Description
   * - ``user_detail_dict``
     - ``Dict[str, Any]``
     - (required)
     - User template selector. ``{"user": "fast_http_user"}`` /
       ``"http_user"`` / ``"websocket_user"`` / ``"grpc_user"`` /
       ``"mqtt_user"`` / ``"socket_user"``.
   * - ``user_count``
     - ``int``
     - ``50``
     - Total number of simulated users to spawn.
   * - ``spawn_rate``
     - ``int``
     - ``10``
     - Users spawned per second.
   * - ``test_time``
     - ``Optional[int]``
     - ``60``
     - Test duration in seconds; ``None`` runs until interrupted.
   * - ``web_ui_dict``
     - ``Optional[Dict]``
     - ``None``
     - Enable Locust Web UI, e.g. ``{"host": "127.0.0.1", "port": 8089}``.
   * - ``runner_mode``
     - ``str``
     - ``"local"``
     - ``"local"``, ``"master"``, or ``"worker"``.
   * - ``master_bind_host`` / ``master_bind_port``
     - ``str`` / ``int``
     - ``"*"`` / ``5557``
     - Used by master to bind its control plane.
   * - ``master_host`` / ``master_port``
     - ``str`` / ``int``
     - ``"127.0.0.1"`` / ``5557``
     - Used by workers to connect to the master.
   * - ``expected_workers``
     - ``int``
     - ``0``
     - Master waits up to 60 s for this many workers before ramping.
   * - ``**kwargs``
     - —
     - —
     - Forwarded to the user template (e.g. ``tasks``, ``variables``,
       ``csv_sources``, protocol-specific fields).

**Returns:** ``Dict[str, Any]`` — Summary of the test configuration.

**Raises:** ``ValueError`` — If an unsupported user type is specified.

**Example:**

.. code-block:: python

    from je_load_density import start_test

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=30,
        variables={"base": "https://httpbin.org"},
        tasks=[
            {"method": "get", "request_url": "${var.base}/get"},
            {"method": "post", "request_url": "${var.base}/post",
             "json": {"hello": "world"}},
        ],
    )

prepare_env()
-------------

Lower-level helper behind ``start_test``: builds a Locust
``Environment`` in the requested mode and starts the runner.

.. code-block:: python

    def prepare_env(
        user_class,
        user_count: int = 50,
        spawn_rate: int = 10,
        test_time: int = 60,
        web_ui_dict: dict = None,
        runner_mode: str = "local",
        master_bind_host: str = "*",
        master_bind_port: int = 5557,
        master_host: str = "127.0.0.1",
        master_port: int = 5557,
        expected_workers: int = 0,
        **kwargs,
    ) -> None

create_env()
------------

Build a Locust ``Environment`` with a local runner and the stats
greenlets attached. Useful for embedding LoadDensity inside another
process.

.. code-block:: python

    def create_env(user_class, another_event=events) -> Environment

TestRecord
----------

Stores success and failure records collected by the Locust request
hook (registered automatically on import).

.. code-block:: python

    class TestRecord:
        test_record_list: List[Dict]    # Success records
        error_record_list: List[Dict]   # Failure records

        def clear_records(self) -> None: ...

**Global instance:** ``test_record_instance``

**Success record fields:**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``Method``
     - ``str``
     - HTTP method or protocol verb.
   * - ``test_url`` / ``name``
     - ``str``
     - Target URL and Locust event name (defaults to URL).
   * - ``status_code``
     - ``str``
     - HTTP status code or protocol equivalent.
   * - ``response_time_ms``
     - ``int``
     - Wall-clock latency in milliseconds.
   * - ``response_length``
     - ``int``
     - Response body length in bytes.
   * - ``error``
     - ``None``
     - Always ``None`` for success records.

**Failure record fields** mirror the success shape but ``error``
carries the exception message and ``status_code`` may be ``None``
when the request never received a response.

**Example:**

.. code-block:: python

    from je_load_density import test_record_instance

    for record in test_record_instance.test_record_list:
        print(record["Method"], record["test_url"], record["status_code"])

    for error in test_record_instance.error_record_list:
        print(error["Method"], error["test_url"], error["error"])

    test_record_instance.clear_records()

locust_wrapper_proxy
--------------------

The per-protocol task store referenced by every user template. The
``set_wrapper_*_user`` helpers (one per template) push the configured
tasks into this proxy before ``prepare_env`` boots Locust.

.. code-block:: python

    from je_load_density import locust_wrapper_proxy

    # Inspect the active task list for the current user type
    print(locust_wrapper_proxy.tasks_dict)

request_hook
------------

A Locust event listener that wires each completed (or failed) request
to ``test_record_instance``. Registered on package import; no manual
setup required.
