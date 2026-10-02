Test Record
===========

Overview
--------

``test_record_instance`` is the in-memory store that the Locust
``request`` hook feeds. Every report generator (HTML / JSON / XML / CSV
/ JUnit / summary) reads from this object, and the SQLite persistence
helpers write it to disk.

Record fields
-------------

Each entry is a dict with the following keys:

* ``Method`` — HTTP method or protocol tag (``GET``, ``POST``, ``WS``,
  ``GRPC``, ``MQTT``, ``TCP``, ``UDP``).
* ``test_url`` — Target URL or address.
* ``name`` — Locust event name (``request_url`` if not overridden).
* ``status_code`` — Response status (string) or ``None``.
* ``response_time_ms`` — Locust-reported response time in ms.
* ``response_length`` — Response size in bytes.
* ``error`` — ``None`` for success rows; the exception string for
  failures.
* ``start_time`` — When Locust started the request (epoch seconds), or
  ``None``. Successes and failures sit in two lists; reports that need
  request order (service map, Allure) sort by this.
* ``text``, ``content``, ``headers`` — Optional, only present on HTTP
  successes.

Clearing between runs
---------------------

.. code-block:: python

    from je_load_density import test_record_instance
    test_record_instance.clear_records()

or via the executor::

    ["LD_clear_records", {}]

SQLite persistence
------------------

See :doc:`../../../En/doc/sqlite_persistence/sqlite_persistence_doc`.

Canonical run-scoped results
---------------------------

The opt-in ``utils.test_record.run_context`` module re-exports ActionCore's
``RunContext`` and ``use_run_context``. It requires the coordinated core request-record API;
legacy package imports and lists remain compatible with earlier core releases.
Create a context with ``source="loaddensity"``, ``phase="load"`` and the chosen engine.
Pass ``run_context=context`` to ``run_async_load`` or ``start_test``. Locust binds the context
to isolated environment events so greenlets do not depend on ContextVar inheritance.
``context.to_json()`` exports v1 records with identities, numeric/null status and structured errors.
Payload capture is disabled by default. Async summaries exclude previous invocations' records.

Canonical SQLite export uses `persist_canonical_records(database_path, context)` and `fetch_canonical_records(database_path, run_id)` from `utils.test_record.sqlite_persistence`. Separate `request_runs_v1` / `request_records_v1` tables preserve legacy runs. Writes validate snapshots, deduplicate identical IDs, reject conflicting retries and roll back the entire batch on failure. Reads revalidate stored records. JSON export is `context.to_json()`.
