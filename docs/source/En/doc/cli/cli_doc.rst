CLI (Command Line Interface)
============================

LoadDensity provides a full command-line interface via ``python -m je_load_density``.

CLI Arguments
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Argument
     - Short
     - Description
   * - ``--execute_file``
     - ``-e``
     - Execute a single JSON script file
   * - ``--execute_dir``
     - ``-d``
     - Execute all JSON files in a directory
   * - ``--execute_str``
     - —
     - Execute an inline JSON string
   * - ``--create_project``
     - ``-c``
     - Scaffold a new project with templates

Execute a Single JSON File
--------------------------

Run a test defined in a single JSON keyword file:

.. code-block:: bash

    python -m je_load_density -e test_scenario.json

The JSON file should follow the action list format:

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

Execute All JSON Files in a Directory
-------------------------------------

Run all JSON keyword files in a specified directory recursively:

.. code-block:: bash

    python -m je_load_density -d ./test_scripts/

This scans the directory for all ``.json`` files and executes each one sequentially.

Execute an Inline JSON String
-----------------------------

Execute a JSON action list directly as a string:

.. code-block:: bash

    python -m je_load_density --execute_str '[["LD_start_test", {"user_detail_dict": {"user": "fast_http_user"}, "user_count": 10, "spawn_rate": 5, "test_time": 5, "tasks": {"get": {"request_url": "http://httpbin.org/get"}}}]]'

.. note::

    On **Windows**, inline JSON strings are automatically double-parsed due to shell
    escaping differences. The CLI handles this transparently.

Create a Project
----------------

Scaffold a new project with keyword templates and executor scripts:

.. code-block:: bash

    python -m je_load_density -c MyProject

This generates a project directory structure:

.. code-block:: text

    MyProject/
    └── LoadDensity/
        ├── keyword/
        │   ├── keyword1.json
        │   └── keyword2.json
        └── executor/
            ├── executor_one_file.py
            └── executor_folder.py

Error Handling
--------------

If no valid argument is provided, the CLI raises a ``LoadDensityTestExecuteException``
and exits with code 1. All errors are printed to stderr.
