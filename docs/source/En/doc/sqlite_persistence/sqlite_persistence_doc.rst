SQLite Persistence
==================

Overview
--------

The SQLite sink writes the in-memory ``test_record_instance`` to a
SQLite database so runs can be compared, regression-checked, or shipped
to another tool. The schema is created lazily; an empty file is fine.

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

Indexes are created on ``run_id`` and ``name`` to keep cross-run
queries fast.

Action JSON
-----------

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

Use ``LD_list_runs`` and ``LD_fetch_run_records`` from later scripts to
read back the data.
