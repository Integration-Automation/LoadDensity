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
