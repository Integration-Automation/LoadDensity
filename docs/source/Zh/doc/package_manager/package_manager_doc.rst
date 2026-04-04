動態套件載入
============

``PackageManager`` 可讓您在執行時動態匯入 Python 套件，並將其所有公開函式註冊到
執行器的事件字典中。

基本用法
--------

.. code-block:: python

    from je_load_density import executor

    # 載入套件並將其所有函式註冊為執行器動作
    executor.execute_action([
        ["LD_add_package_to_executor", ["my_custom_package"]]
    ])

載入後，套件中的所有函式都可以透過名稱在 JSON 腳本或
``executor.execute_action()`` 中呼叫。

運作原理
--------

1. 使用 ``importlib.util.find_spec()`` 定位套件
2. 使用 ``importlib.import_module()`` 匯入套件
3. 使用 ``inspect.getmembers()`` 搭配 ``isfunction`` 找出套件中所有函式
4. 將每個函式註冊到執行器的 ``event_dict``

.. note::

    僅會註冊套件中的頂層函式。類別、常數和子模組不會自動加入。

PackageManager API
------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - 方法
     - 說明
   * - ``load_package_if_available(package)``
     - 嘗試匯入套件。回傳模組或 ``None``（若未找到）。
   * - ``add_package_to_executor(package)``
     - 匯入套件並將其所有函式註冊到執行器。

範例：使用自訂套件
-------------------

假設您有一個自訂套件 ``my_utils``，其中包含 ``compute()`` 函式：

.. code-block:: python

    from je_load_density import executor

    # 註冊套件
    executor.execute_action([
        ["LD_add_package_to_executor", ["my_utils"]]
    ])

    # 現在可以透過名稱呼叫 compute()
    executor.execute_action([
        ["compute", [42]]
    ])

在 JSON 腳本中使用
--------------------

.. code-block:: json

    [
        ["LD_add_package_to_executor", ["my_utils"]],
        ["compute", [42]]
    ]
