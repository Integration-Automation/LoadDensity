Getting Started
===============

This guide walks you through the basics of using LoadDensity to run your first load test.

User Types
----------

LoadDensity supports two types of Locust users:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - User Type Key
     - Locust Class
     - Description
   * - ``fast_http_user``
     - ``FastHttpUser``
     - Uses ``geventhttpclient`` for higher throughput. Recommended for most use cases.
   * - ``http_user``
     - ``HttpUser``
     - Uses Python ``requests`` library. Better compatibility, lower throughput.

Supported HTTP Methods
----------------------

LoadDensity supports the following HTTP methods:

* ``get``
* ``post``
* ``put``
* ``patch``
* ``delete``
* ``head``
* ``options``

Running a Test with Python API
------------------------------

The simplest way to run a load test is to call ``start_test()``:

.. code-block:: python

    from je_load_density import start_test

    result = start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=50,
        spawn_rate=10,
        test_time=10,
        tasks={
            "get": {"request_url": "http://httpbin.org/get"},
            "post": {"request_url": "http://httpbin.org/post"},
        }
    )

``start_test()`` Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - Parameter
     - Type
     - Default
     - Description
   * - ``user_detail_dict``
     - ``dict``
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
     - ``int`` or ``None``
     - ``60``
     - Test duration in seconds. Pass ``None`` for unlimited duration
   * - ``web_ui_dict``
     - ``dict`` or ``None``
     - ``None``
     - Enable Locust Web UI. e.g. ``{"host": "127.0.0.1", "port": 8089}``

Return Value
~~~~~~~~~~~~

``start_test()`` returns a dictionary summarizing the test configuration:

.. code-block:: python

    {
        "user_detail": {"user": "fast_http_user"},
        "user_count": 50,
        "spawn_rate": 10,
        "test_time": 10,
        "web_ui": None,
    }

Enabling the Locust Web UI
--------------------------

To monitor the test in real-time through the Locust Web UI:

.. code-block:: python

    from je_load_density import start_test

    result = start_test(
        user_detail_dict={"user": "http_user"},
        user_count=100,
        spawn_rate=20,
        test_time=30,
        web_ui_dict={"host": "127.0.0.1", "port": 8089},
        tasks={
            "get": {"request_url": "http://httpbin.org/get"},
        }
    )

Then open ``http://127.0.0.1:8089`` in your browser to view real-time statistics.

Running a Test with JSON Script Files
-------------------------------------

You can define test scenarios as JSON files and execute them without writing Python code.

Create a ``test_scenario.json`` file:

.. code-block:: json

    [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 50,
            "spawn_rate": 10,
            "test_time": 5,
            "tasks": {
                "get": {"request_url": "http://httpbin.org/get"},
                "post": {"request_url": "http://httpbin.org/post"}
            }
        }]
    ]

Execute from Python:

.. code-block:: python

    from je_load_density import execute_action, read_action_json

    execute_action(read_action_json("test_scenario.json"))

JSON Script Format
~~~~~~~~~~~~~~~~~~

Each JSON script is an array of actions. Each action is a list:

* With keyword arguments: ``["action_name", {"param1": "value1"}]``
* With positional arguments: ``["action_name", ["arg1", "arg2"]]``
* With no arguments: ``["action_name"]``

Chaining Multiple Actions
~~~~~~~~~~~~~~~~~~~~~~~~~

Multiple actions can be chained in a single JSON file. For example, run a test and
generate reports automatically:

.. code-block:: json

    [
        ["LD_start_test", {
            "user_detail_dict": {"user": "fast_http_user"},
            "user_count": 10,
            "spawn_rate": 5,
            "test_time": 5,
            "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
        }],
        ["LD_generate_html_report", {"html_name": "my_report"}],
        ["LD_generate_json_report", {"json_file_name": "my_report"}],
        ["LD_generate_xml_report", {"xml_file_name": "my_report"}]
    ]

Dict-based JSON Format
~~~~~~~~~~~~~~~~~~~~~~~

JSON scripts can also be wrapped in a dict with a ``"load_density"`` key:

.. code-block:: json

    {
        "load_density": [
            ["LD_start_test", {
                "user_detail_dict": {"user": "fast_http_user"},
                "user_count": 10,
                "spawn_rate": 5,
                "test_time": 5,
                "tasks": {"get": {"request_url": "http://httpbin.org/get"}}
            }]
        ]
    }

Project Scaffolding
-------------------

LoadDensity can generate a project directory structure with keyword templates and
executor scripts:

.. code-block:: python

    from je_load_density import create_project_dir

    create_project_dir(project_path="./my_tests", parent_name="LoadDensity")

Or via CLI:

.. code-block:: bash

    python -m je_load_density -c ./my_tests

This creates the following structure:

.. code-block:: text

    my_tests/
    └── LoadDensity/
        ├── keyword/
        │   ├── keyword1.json    # FastHttpUser test template
        │   └── keyword2.json    # HttpUser test template
        └── executor/
            ├── executor_one_file.py   # Execute single keyword file
            └── executor_folder.py     # Execute all files in keyword/

* ``keyword1.json`` — Template using ``fast_http_user`` with sample GET/POST tasks
* ``keyword2.json`` — Template using ``http_user`` with sample GET/POST tasks
* ``executor_one_file.py`` — Python script to execute ``keyword1.json``
* ``executor_folder.py`` — Python script to execute all JSON files in ``keyword/``
