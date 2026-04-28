MCP Server (for Claude)
=======================

Overview
--------

LoadDensity ships a `Model Context Protocol
<https://modelcontextprotocol.io/>`_ server that exposes the framework
as a set of MCP tools. With it, Claude (Desktop, Code, or any MCP
client) can drive load tests, generate reports, import HAR files, and
inspect persisted runs without leaving the chat.

Install
-------

.. code-block:: bash

    pip install "je_load_density[mcp]"

Run the server
--------------

.. code-block:: bash

    python -m je_load_density.mcp_server

The server speaks MCP over stdio. Wire it into the client of your
choice (Claude Desktop ``claude_desktop_config.json``, Claude Code,
etc.):

.. code-block:: json

    {
      "mcpServers": {
        "loaddensity": {
          "command": "python",
          "args": ["-m", "je_load_density.mcp_server"]
        }
      }
    }

Exposed tools
-------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Tool
     - Purpose
   * - ``load_density.run_test``
     - Run a Locust-backed load test (HTTP / WS / gRPC / MQTT / Socket).
   * - ``load_density.run_action_json``
     - Execute an action JSON document.
   * - ``load_density.create_project``
     - Scaffold a project skeleton at PATH.
   * - ``load_density.list_executor_commands``
     - List every ``LD_*`` command registered in the executor.
   * - ``load_density.import_har``
     - Convert a HAR file into a runnable action JSON.
   * - ``load_density.generate_reports``
     - Emit any combination of HTML / JSON / XML / CSV / JUnit / summary.
   * - ``load_density.summary``
     - Return aggregated stats (totals, per-name p50/p90/p95/p99).
   * - ``load_density.persist_records``
     - Save the current records into a SQLite database.
   * - ``load_density.list_runs``
     - List recent persisted runs.
   * - ``load_density.fetch_run``
     - Fetch records belonging to a saved run.
   * - ``load_density.clear_records``
     - Drop in-memory records before a new run.
