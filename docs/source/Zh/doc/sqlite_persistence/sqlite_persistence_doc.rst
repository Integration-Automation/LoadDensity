SQLite 持久化
=============

概觀
----

SQLite sink 將記憶體 ``test_record_instance`` 寫入 SQLite 資料庫，便於跨次比對、回歸檢查或匯出至其他工具。Schema 採延遲建立；空檔案即可使用。

Python API
----------

.. code-block:: python

    from je_load_density import (
        persist_records, list_runs, fetch_run_records,
    )

    run_id = persist_records(
        "loadtests.db",
        label="checkout-2026-04-28",
        metadata={"branch": "dev", "commit": "abc1234"},
    )

    for row in list_runs("loadtests.db", limit=10):
        print(row)

    for record in fetch_run_records("loadtests.db", run_id):
        print(record)

Schema
------

* ``load_density_runs(id, started_at, label, metadata_json)``
* ``load_density_records(id, run_id, outcome, method, test_url, name,
  status_code, response_time_ms, response_length, error)``

``run_id`` 與 ``name`` 上建立索引以加速跨次查詢。

動作 JSON
---------

.. code-block:: json

    {"load_density": [
      ["LD_clear_records", {}],
      ["LD_start_test", {...}],
      ["LD_persist_records", {
        "database_path": "loadtests.db",
        "label": "checkout",
        "metadata": {"branch": "dev"}
      }]
    ]}

之後的腳本以 ``LD_list_runs`` 與 ``LD_fetch_run_records`` 讀取資料。
