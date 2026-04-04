LoadDensity Core API
====================

The core API provides the main entry points for starting load tests, creating Locust
environments, and accessing test records.

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
        **kwargs
    ) -> Dict[str, Any]

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - Parameter
     - Type
     - Default
     - Description
   * - ``user_detail_dict``
     - ``Dict[str, Any]``
     - (required)
     - User type configuration. ``{"user": "fast_http_user"}`` or ``{"user": "http_user"}``
   * - ``user_count``
     - ``int``
     - ``50``
     - Total number of simulated users to spawn
   * - ``spawn_rate``
     - ``int``
     - ``10``
     - Number of users spawned per second
   * - ``test_time``
     - ``Optional[int]``
     - ``60``
     - Test duration in seconds. Pass ``None`` for unlimited duration
   * - ``web_ui_dict``
     - ``Optional[Dict]``
     - ``None``
     - Enable Locust Web UI. e.g. ``{"host": "127.0.0.1", "port": 8089}``
   * - ``**kwargs``
     - —
     - —
     - Additional parameters passed to user initialization

**Returns:** ``Dict[str, Any]`` — Summary dictionary of the test configuration.

**Raises:** ``ValueError`` — If an unsupported user type is specified.

**Example:**

.. code-block:: python

    from je_load_density import start_test

    result = start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=10,
        tasks={
            "get": {"request_url": "http://httpbin.org/get"},
        }
    )

prepare_env()
-------------

Create a Locust environment, start the runner, and block until the test completes.

.. code-block:: python

    def prepare_env(
        user_class: List[User],
        user_count: int = 50,
        spawn_rate: int = 10,
        test_time: int = 60,
        web_ui_dict: dict = None,
        **kwargs
    ) -> None

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - Parameter
     - Type
     - Default
     - Description
   * - ``user_class``
     - ``List[User]``
     - (required)
     - Locust user class to run
   * - ``user_count``
     - ``int``
     - ``50``
     - Number of users to spawn
   * - ``spawn_rate``
     - ``int``
     - ``10``
     - Users spawned per second
   * - ``test_time``
     - ``int``
     - ``60``
     - Test duration in seconds
   * - ``web_ui_dict``
     - ``dict``
     - ``None``
     - Web UI configuration ``{"host": str, "port": int}``

create_env()
------------

Create a Locust ``Environment`` with a local runner and stats collection greenlets.

.. code-block:: python

    def create_env(
        user_class: List[User],
        another_event: events = events
    ) -> Environment

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Type
     - Description
   * - ``user_class``
     - ``List[User]``
     - Locust user class
   * - ``another_event``
     - ``events``
     - Custom Locust event instance (default: ``locust.events``)

**Returns:** ``locust.env.Environment`` — Configured Locust environment with local runner.

TestRecord
----------

Stores success and failure test records collected by the request hook.

.. code-block:: python

    class TestRecord:
        test_record_list: List[Dict]    # Success records
        error_record_list: List[Dict]   # Failure records

        def clear_records(self) -> None: ...

**Global instance:** ``test_record_instance``

**Success record fields:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``Method``
     - ``str``
     - HTTP method (GET, POST, etc.)
   * - ``test_url``
     - ``str``
     - Request URL
   * - ``name``
     - ``str``
     - Request name (Locust grouping name)
   * - ``status_code``
     - ``str``
     - HTTP status code
   * - ``text``
     - ``str``
     - Response body text
   * - ``content``
     - ``str``
     - Response body content (bytes as string)
   * - ``headers``
     - ``str``
     - Response headers
   * - ``error``
     - ``None``
     - Always ``None`` for success records

**Failure record fields:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Field
     - Type
     - Description
   * - ``Method``
     - ``str``
     - HTTP method
   * - ``test_url``
     - ``str``
     - Request URL
   * - ``name``
     - ``str``
     - Request name
   * - ``status_code``
     - ``str`` or ``None``
     - HTTP status code (if available)
   * - ``text``
     - ``str`` or ``None``
     - Response body text (if available)
   * - ``error``
     - ``str``
     - Exception message

**Example:**

.. code-block:: python

    from je_load_density import test_record_instance

    for record in test_record_instance.test_record_list:
        print(record["Method"], record["test_url"], record["status_code"])

    for error in test_record_instance.error_record_list:
        print(error["Method"], error["test_url"], error["error"])

    test_record_instance.clear_records()

request_hook
------------

A Locust event listener that automatically records all requests during test execution.
Registered via ``@events.request.add_listener``.

This hook is loaded automatically when importing ``je_load_density`` and requires no
manual configuration.
