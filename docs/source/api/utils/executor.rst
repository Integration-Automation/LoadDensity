Executor API
============

The ``Executor`` class is the core event-driven system in LoadDensity. It maintains an
``event_dict`` that maps string action names to callable functions.

Executor Class
--------------

.. code-block:: python

    class Executor:
        event_dict: dict[str, Any]

        def execute_action(self, action_list: Union[list, dict]) -> dict[str, Any]: ...
        def execute_files(self, execute_files_list: list[str]) -> list[dict[str, Any]]: ...

execute_action()
~~~~~~~~~~~~~~~~

Execute a list of actions.

.. code-block:: python

    def execute_action(self, action_list: Union[list, dict]) -> dict[str, Any]

**Parameters:**

* ``action_list`` — A list of actions, where each action is:

  * ``["action_name", {"kwarg1": value}]`` — Call with keyword arguments
  * ``["action_name", [arg1, arg2]]`` — Call with positional arguments
  * ``["action_name"]`` — Call with no arguments

  Can also be a dict with a ``"load_density"`` key containing the action list.

**Returns:** ``dict[str, Any]`` — Execution record dictionary mapping action descriptions
to return values.

execute_files()
~~~~~~~~~~~~~~~

Execute actions from multiple JSON files.

.. code-block:: python

    def execute_files(self, execute_files_list: list[str]) -> list[dict[str, Any]]

**Parameters:**

* ``execute_files_list`` — List of JSON file paths to execute

**Returns:** ``list[dict[str, Any]]`` — List of execution results per file.

add_command_to_executor()
-------------------------

Add custom commands to the global executor.

.. code-block:: python

    def add_command_to_executor(command_dict: dict[str, Any]) -> None

**Parameters:**

* ``command_dict`` — Dictionary mapping command names to functions.
  Only ``types.MethodType`` and ``types.FunctionType`` are accepted.

**Raises:** ``LoadDensityTestExecuteException`` — If a non-callable is provided.

**Example:**

.. code-block:: python

    from je_load_density import add_command_to_executor, executor

    def my_action(msg):
        print(f"Custom: {msg}")

    add_command_to_executor({"my_action": my_action})
    executor.execute_action([["my_action", ["Hello"]]])

Built-in Actions
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Action Name
     - Description
   * - ``LD_start_test``
     - Start a load test
   * - ``LD_generate_html``
     - Generate HTML fragments (returns data)
   * - ``LD_generate_html_report``
     - Generate HTML report file
   * - ``LD_generate_json``
     - Generate JSON data structures (returns data)
   * - ``LD_generate_json_report``
     - Generate JSON report files
   * - ``LD_generate_xml``
     - Generate XML strings (returns data)
   * - ``LD_generate_xml_report``
     - Generate XML report files
   * - ``LD_execute_action``
     - Execute a list of actions (recursive)
   * - ``LD_execute_files``
     - Execute actions from multiple files
   * - ``LD_add_package_to_executor``
     - Dynamically load a package into executor

Additionally, all Python built-in functions (``print``, ``len``, ``type``, etc.) are
automatically registered.

Global Convenience Functions
----------------------------

.. code-block:: python

    def execute_action(action_list: list) -> dict[str, Any]
    def execute_files(execute_files_list: list[str]) -> list[dict[str, Any]]

These call the corresponding methods on the global ``executor`` instance.
