Callback Executor
=================

The ``CallbackFunctionExecutor`` allows chaining a trigger function with a callback function.
This is useful for post-test workflows — for example, run a test, then automatically
generate a report.

Basic Usage
-----------

.. code-block:: python

    from je_load_density import callback_executor

    def after_test():
        print("Test finished, generating report...")

    callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=after_test,
        user_detail_dict={"user": "fast_http_user"},
        user_count=10,
        spawn_rate=5,
        test_time=5,
        tasks={"get": {"request_url": "http://httpbin.org/get"}},
    )

How It Works
------------

1. The ``trigger_function_name`` is looked up in the executor's ``event_dict``
2. The trigger function is executed with the provided ``**kwargs``
3. After the trigger function completes, the ``callback_function`` is called
4. The return value of the trigger function is returned

Available Trigger Functions
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Trigger Name
     - Function
   * - ``user_test``
     - ``start_test()`` — Run a load test
   * - ``LD_generate_html``
     - ``generate_html()`` — Generate HTML fragments
   * - ``LD_generate_html_report``
     - ``generate_html_report()`` — Generate HTML report file
   * - ``LD_generate_json``
     - ``generate_json()`` — Generate JSON data
   * - ``LD_generate_json_report``
     - ``generate_json_report()`` — Generate JSON report files
   * - ``LD_generate_xml``
     - ``generate_xml()`` — Generate XML strings
   * - ``LD_generate_xml_report``
     - ``generate_xml_report()`` — Generate XML report files

Passing Parameters to Callbacks
---------------------------------

With keyword arguments (default):

.. code-block:: python

    def my_callback(report_name, format_type):
        print(f"Generating {format_type} report: {report_name}")

    callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=my_callback,
        callback_function_param={"report_name": "final", "format_type": "html"},
        callback_param_method="kwargs",
        user_detail_dict={"user": "fast_http_user"},
        user_count=10,
        spawn_rate=5,
        test_time=5,
        tasks={"get": {"request_url": "http://httpbin.org/get"}},
    )

With positional arguments:

.. code-block:: python

    def my_callback(arg1, arg2):
        print(f"Args: {arg1}, {arg2}")

    callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=my_callback,
        callback_function_param=["value1", "value2"],
        callback_param_method="args",
        user_detail_dict={"user": "fast_http_user"},
        user_count=10,
        spawn_rate=5,
        test_time=5,
        tasks={"get": {"request_url": "http://httpbin.org/get"}},
    )

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Type
     - Description
   * - ``trigger_function_name``
     - ``str``
     - Name of function in ``event_dict`` to trigger
   * - ``callback_function``
     - ``Callable``
     - Callback function to execute after the trigger
   * - ``callback_function_param``
     - ``dict`` or ``list`` or ``None``
     - Parameters for the callback (dict for kwargs, list for args)
   * - ``callback_param_method``
     - ``str``
     - ``"kwargs"`` (default) or ``"args"``
   * - ``**kwargs``
     - —
     - Parameters passed to the trigger function

Error Handling
--------------

* ``CallbackExecutorException`` is raised if:

  * ``trigger_function_name`` is not found in ``event_dict``
  * ``callback_param_method`` is not ``"kwargs"`` or ``"args"``
