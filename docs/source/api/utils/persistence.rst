SQLite Persistence API
======================

The persistence layer offers an optional SQLite sink for the
in-memory ``test_record_instance`` so runs can be compared over time.

persist_records()
-----------------

.. code-block:: python

    from je_load_density import persist_records

    run_id = persist_records(
        "loadtests.db",
        label="checkout-2026-04-28",
        metadata={"branch": "dev", "commit": "abc1234"},
    )

Writes one row into the ``runs`` table (label, started_at, finished_at,
counters) and one row per request into the ``records`` table. Returns
the new ``run_id`` (integer primary key).

list_runs()
-----------

.. code-block:: python

    from je_load_density import list_runs

    for row in list_runs("loadtests.db", limit=10):
        print(row["id"], row["label"], row["total"], row["failed"])

Returns recent runs sorted by ``id`` descending. Each row is a dict
matching the ``runs`` schema.

fetch_run_records()
-------------------

.. code-block:: python

    from je_load_density import fetch_run_records

    records = fetch_run_records("loadtests.db", run_id=42)

Returns every record belonging to one run as a list of dicts. Suitable
for cross-run regression analysis.

Schema
------

Tables are created lazily on first write; an empty file is fine.

.. code-block:: sql

    CREATE TABLE runs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        label        TEXT,
        started_at   TEXT,
        finished_at  TEXT,
        total        INTEGER,
        failed       INTEGER,
        metadata     TEXT  -- JSON blob
    );

    CREATE TABLE records (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id            INTEGER NOT NULL REFERENCES runs(id),
        outcome           TEXT NOT NULL,            -- 'success' | 'failure'
        method            TEXT,
        name              TEXT,
        url               TEXT,
        status_code       TEXT,
        response_time_ms  INTEGER,
        response_length   INTEGER,
        error             TEXT
    );

    CREATE INDEX idx_records_run_id ON records(run_id);
    CREATE INDEX idx_records_name   ON records(name);

Action-JSON commands
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Command
     - Summary
   * - ``LD_persist_records``
     - Save in-memory records to SQLite.
   * - ``LD_list_runs``
     - List recent runs in a database.
   * - ``LD_fetch_run_records``
     - Load every record for one run.
   * - ``LD_clear_records``
     - Drop the in-memory record list (does not touch SQLite).
