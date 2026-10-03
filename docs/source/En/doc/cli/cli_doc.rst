CLI (Command Line Interface)
============================

LoadDensity ships a subcommand-style CLI. Run
``python -m je_load_density --help`` for the full surface.

Subcommands
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Subcommand
     - Purpose
   * - ``run FILE``
     - Execute one action JSON file.
   * - ``run-dir DIR``
     - Execute every ``.json`` in a directory.
   * - ``run-str JSON``
     - Execute an inline JSON string (Windows double-encoding handled
       transparently).
   * - ``init PATH``
     - Scaffold a new project skeleton.
   * - ``serve``
     - Start the hardened TCP control socket server.

``run``
-------

.. code-block:: bash

    python -m je_load_density run smoke.json

Where ``smoke.json`` is::

    {"load_density": [
      ["LD_start_test", {
        "user_detail_dict": {"user": "fast_http_user"},
        "user_count": 20, "spawn_rate": 10, "test_time": 30,
        "tasks": [{"method": "get", "request_url": "https://httpbin.org/get"}]
      }],
      ["LD_generate_summary_report", {"report_name": "smoke"}]
    ]}

``run-dir``
-----------

Run every ``.json`` action file in a directory tree::

    python -m je_load_density run-dir ./scenarios

``run-str``
-----------

Inline JSON (handy for CI scripts)::

    python -m je_load_density run-str '{"load_density":[["LD_summary",{}]]}'

``init``
--------

Scaffold a project at PATH::

    python -m je_load_density init ./my_load_test

``serve``
---------

Start the control socket server. See
:doc:`../socket_server/socket_server_doc` for protocol details.

.. code-block:: bash

    python -m je_load_density serve \
        --host 0.0.0.0 --port 9940 \
        --framed --token "$LOAD_DENSITY_SOCKET_TOKEN" \
        --tls-cert /etc/loaddensity/server.crt \
        --tls-key /etc/loaddensity/server.key

Legacy flags
------------

The flat ``-e/-d/-c/--execute_str`` flags from previous releases are
still accepted (suppressed in ``--help``) for backwards compatibility
with tools such as PyBreeze. New scripts should use the subcommands.

Smoke tests and failure exit codes
----------------------------------

``run``, ``run-dir``, ``run-str`` and legacy execute flags return a nonzero exit code when an action (including an SLA gate) fails. Actions in a file still run in order and produce their usual reports. The Python executor return format is preserved. Base installation includes httpx for the native async benchmark; HTTP/2 needs the ``http2`` extra.

Run ``python -m unittest discover -s test/smoke -p "test_*.py"`` from a checkout. The stdlib harness starts a separate local HTTP server and subprocesses to verify real Locust/async requests, summary/JSON/JUnit files, SQLite, SLA failures, dashboard JSON/SSE and MCP initialization. Docker runs the same harness outside the source tree against an installed wheel.


The reusable extras workflow tests an installed checkout wheel in Docker: every declared extra on Python 3.12 and base on 3.10/3.14 for pull requests; all supported Python minors for scheduled runs. Missing capabilities fail rather than skip. Separate Compose health checks exercise Redis/MQTT adapters and a local SQLite query. The etcd extra uses etcd3gw without downgrading protobuf; existing step formats and legacy etcd3 installations remain supported.
