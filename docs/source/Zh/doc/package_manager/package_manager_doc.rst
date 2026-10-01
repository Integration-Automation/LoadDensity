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

套件閘門
--------

``LD_add_package_to_executor`` 能載入 ``os`` 或 ``subprocess``，所以哪些套件可以載入，由宿主程式決定：

.. code-block:: python

    from je_load_density import executor

    executor.allow_packages("my_utils")            # 這些套件與其子模組
    executor.set_allow_arbitrary_packages(False)   # 其他套件在匯入前就拒絕

這兩個開關都不是 action 命令，所以 action 檔（或 socket 用戶端）不能自己打開閘門。被拒絕的套件不會被匯入，
該動作的結果是 ``LoadDensityTestExecuteException``。``set_allow_arbitrary_packages(True)`` 則載入任何套件、
不發警告。宿主程式呼叫任一個開關之前，任何套件仍會載入，但會發出 ``DeprecationWarning``；之後的版本會預設
拒絕允許清單以外的套件。
