Callback Function API
=====================

The ``CallbackFunctionExecutor`` provides a mechanism to trigger a function from its
event dictionary, then execute a callback function.

CallbackFunctionExecutor Class
-------------------------------

.. code-block:: python

    class CallbackFunctionExecutor:
        event_dict: dict[str, Callable]

        def callback_function(
            self,
            trigger_function_name: str,
            callback_function: Callable,
            callback_function_param: Optional[Union[dict, list]] = None,
            callback_param_method: str = "kwargs",
            **kwargs
        ) -> Any: ...

callback_function()
~~~~~~~~~~~~~~~~~~~

Execute a trigger function from ``event_dict``, then call the callback function.

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

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
     - ``dict``, ``list``, or ``None``
     - Parameters for callback (dict for kwargs, list for args)
   * - ``callback_param_method``
     - ``str``
     - ``"kwargs"`` (default) or ``"args"``
   * - ``**kwargs``
     - —
     - Parameters passed to the trigger function

**Returns:** Return value of the trigger function.

**Raises:** ``CallbackExecutorException`` — If trigger function not found or invalid
param method.

Available Trigger Functions
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Trigger Name
     - Function
   * - ``user_test``
     - ``start_test()``
   * - ``LD_generate_html``
     - ``generate_html()``
   * - ``LD_generate_html_report``
     - ``generate_html_report()``
   * - ``LD_generate_json``
     - ``generate_json()``
   * - ``LD_generate_json_report``
     - ``generate_json_report()``
   * - ``LD_generate_xml``
     - ``generate_xml()``
   * - ``LD_generate_xml_report``
     - ``generate_xml_report()``

**Global instance:** ``callback_executor``
