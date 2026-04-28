Architecture
============

Overview
--------

LoadDensity is a thin facade over Locust that adds a JSON-driven action
executor, a multi-protocol user template registry, scenario flow, data
parameterisation, observability sinks, and an MCP control surface.

The dependency direction always points from the action layer down to
Locust, never the other way around — your action JSON defines what to
do, the executor maps each command to a Python callable, and Locust
runs the resulting load.

Layered view
------------

.. mermaid::

    flowchart TB
      cli[CLI / MCP / GUI / Socket Server] --> exec[Action Executor]
      exec --> start[start_test]
      start --> proxy[locust_wrapper_proxy]
      proxy --> userhttp[HTTP / FastHttp Wrapper]
      proxy --> userws[WebSocket Wrapper]
      proxy --> usergrpc[gRPC Wrapper]
      proxy --> usermqtt[MQTT Wrapper]
      proxy --> usersock[Raw TCP/UDP Wrapper]
      userhttp & userws & usergrpc & usermqtt & usersock --> hooks[Locust events]
      hooks --> records[test_record_instance]
      hooks --> exporters[Prometheus / Influx / OTel]
      records --> reports[HTML / JSON / XML / CSV / JUnit / Summary]
      records --> sqlite[SQLite persistence]

Module map
----------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module
     - Purpose
   * - ``je_load_density.utils.executor``
     - ``Executor`` class, dispatch table, ``execute_action`` /
       ``execute_files`` entrypoints.
   * - ``je_load_density.utils.parameterization``
     - ``ParameterResolver`` for ``${var.x}`` / ``${env.X}`` /
       ``${csv.s.col}`` / ``${faker.method}`` / built-in helpers.
   * - ``je_load_density.utils.recording``
     - HAR ingestion → action JSON.
   * - ``je_load_density.utils.metrics``
     - Prometheus exporter, InfluxDB sink, OpenTelemetry exporter.
   * - ``je_load_density.utils.test_record``
     - In-memory record list plus optional SQLite sink.
   * - ``je_load_density.utils.generate_report``
     - HTML / JSON / XML / CSV / JUnit / summary generators.
   * - ``je_load_density.utils.socket_server``
     - Length-framed TCP control plane with optional TLS and token.
   * - ``je_load_density.wrapper.proxy``
     - Per-protocol proxy holding the configured tasks for each user
       template.
   * - ``je_load_density.wrapper.user_template``
     - Locust user classes for HTTP, FastHttp, WebSocket, gRPC, MQTT,
       and raw socket.
   * - ``je_load_density.wrapper.start_wrapper``
     - ``start_test`` dispatcher that picks a user template and forwards
       to ``prepare_env``.
   * - ``je_load_density.wrapper.create_locust_env``
     - ``prepare_env`` / ``create_env`` building a Locust environment in
       local, master, or worker mode.
   * - ``je_load_density.mcp_server``
     - MCP server exposing 11 tools so Claude can drive LoadDensity.
   * - ``je_load_density.gui``
     - Optional PySide6 widgets (form controls + live stats panel).

Action lifecycle
----------------

#. Caller submits an action JSON via the CLI, MCP tool, socket server,
   or direct ``execute_action(...)`` call.
#. ``Executor.execute_action`` dispatches each step against
   ``event_dict`` (``LD_*`` commands plus safe builtins).
#. When the step is ``LD_start_test``, the dispatcher selects a user
   template (``http_user``, ``fast_http_user``, ``websocket_user``,
   ``grpc_user``, ``mqtt_user``, ``socket_user``), seeds the parameter
   resolver from any ``variables`` / ``csv_sources``, and calls
   ``prepare_env``.
#. ``prepare_env`` builds a Locust ``Environment`` in local, master, or
   worker mode and starts the run.
#. Each user runs ``run_scenario`` (or the protocol equivalent) per
   tick, fires Locust events, and feeds ``test_record_instance``.
#. Reports, metrics exporters, and SQLite persistence consume the
   accumulated records.
