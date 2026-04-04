回呼執行器
==========

``CallbackFunctionExecutor`` 可將觸發函式與回呼函式串連。
這對於測試後的工作流程非常有用 — 例如，執行測試後自動產生報告。

基本用法
--------

.. code-block:: python

    from je_load_density import callback_executor

    def after_test():
        print("測試完成，正在產生報告...")

    callback_executor.callback_function(
        trigger_function_name="user_test",
        callback_function=after_test,
        user_detail_dict={"user": "fast_http_user"},
        user_count=10,
        spawn_rate=5,
        test_time=5,
        tasks={"get": {"request_url": "http://httpbin.org/get"}},
    )

運作原理
--------

1. 在執行器的 ``event_dict`` 中查找 ``trigger_function_name``
2. 使用提供的 ``**kwargs`` 執行觸發函式
3. 觸發函式完成後，呼叫 ``callback_function``
4. 回傳觸發函式的回傳值

可用的觸發函式
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 觸發名稱
     - 函式
   * - ``user_test``
     - ``start_test()`` — 執行負載測試
   * - ``LD_generate_html``
     - ``generate_html()`` — 產生 HTML 片段
   * - ``LD_generate_html_report``
     - ``generate_html_report()`` — 產生 HTML 報告檔案
   * - ``LD_generate_json``
     - ``generate_json()`` — 產生 JSON 資料
   * - ``LD_generate_json_report``
     - ``generate_json_report()`` — 產生 JSON 報告檔案
   * - ``LD_generate_xml``
     - ``generate_xml()`` — 產生 XML 字串
   * - ``LD_generate_xml_report``
     - ``generate_xml_report()`` — 產生 XML 報告檔案

傳遞參數給回呼函式
--------------------

使用關鍵字參數（預設）：

.. code-block:: python

    def my_callback(report_name, format_type):
        print(f"正在產生 {format_type} 報告：{report_name}")

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

使用位置參數：

.. code-block:: python

    def my_callback(arg1, arg2):
        print(f"參數：{arg1}, {arg2}")

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

參數說明
--------

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 參數
     - 類型
     - 說明
   * - ``trigger_function_name``
     - ``str``
     - ``event_dict`` 中要觸發的函式名稱
   * - ``callback_function``
     - ``Callable``
     - 觸發後要執行的回呼函式
   * - ``callback_function_param``
     - ``dict``、``list`` 或 ``None``
     - 回呼函式的參數（dict 用於 kwargs，list 用於 args）
   * - ``callback_param_method``
     - ``str``
     - ``"kwargs"``（預設）或 ``"args"``
   * - ``**kwargs``
     - —
     - 傳遞給觸發函式的參數

錯誤處理
--------

* 以下情況會拋出 ``CallbackExecutorException``：

  * ``trigger_function_name`` 不在 ``event_dict`` 中
  * ``callback_param_method`` 不是 ``"kwargs"`` 或 ``"args"``
