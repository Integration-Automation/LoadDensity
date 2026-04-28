建立專案
========

概觀
----

``create_project_dir``（CLI: ``je_load_density init``）在指定路徑建立 LoadDensity 專案骨架。骨架包含一份範例動作 JSON、執行腳本，以及資源放置目錄。

Python API
----------

.. code-block:: python

    from je_load_density import create_project_dir
    create_project_dir("./my_load_test")

CLI
---

.. code-block:: bash

    python -m je_load_density init ./my_load_test

結構
----

::

    my_load_test/
    ├── run.py                 # 讀取動作 JSON 的小執行腳本
    └── action.json            # 範例動作 JSON

建立後，編輯 ``action.json``（見 :doc:`../action_executor/action_executor_doc`）並執行::

    python run.py

或::

    python -m je_load_density run action.json
