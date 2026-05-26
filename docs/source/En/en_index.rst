====================================
LoadDensity English Documentation
====================================

The English manual is split into chapters that follow a typical reader
journey: install → run a load test → author actions → harden → scale →
integrate. Use the table of contents on the left, or jump straight to
a chapter below.

.. contents:: On this page
   :local:
   :depth: 1

----

.. _en-getting-started:

Chapter 1 — Getting Started
===========================

Install LoadDensity, run your first load test, and scaffold a project.

.. toctree::
    :maxdepth: 2
    :caption: Getting Started

    doc/installation/installation_doc
    doc/getting_started/getting_started_doc
    doc/create_project/create_project_doc

.. _en-core-api:

Chapter 2 — Core API
====================

The Locust-facing facade: environments, runners, and user proxies.
Read this once and the rest of the framework stops feeling magical.

.. toctree::
    :maxdepth: 2
    :caption: Core API

    doc/architecture/architecture_doc
    doc/start_test/start_test_doc
    doc/locust_env/locust_env_doc

.. _en-actions:

Chapter 3 — Action Authoring & Execution
========================================

Compose JSON-driven action scripts, parameterise data, build scenarios,
and chain post-test callbacks.

.. toctree::
    :maxdepth: 2
    :caption: Actions

    doc/action_executor/action_executor_doc
    doc/parameter_resolver/parameter_resolver_doc
    doc/scenarios/scenarios_doc
    doc/assertions/assertions_doc
    doc/callback/callback_doc
    doc/package_manager/package_manager_doc

.. _en-user-templates:

Chapter 4 — User Templates
==========================

The protocol drivers: HTTP, FastHttp, Async HTTP/2, WebSocket, SSE,
gRPC (unary + streaming), MQTT, raw TCP/UDP, SQL, Redis, Kafka, and
MongoDB. Each template registers as a Locust user with the same task
contract.

.. toctree::
    :maxdepth: 2
    :caption: User Templates

    doc/http_users/http_users_doc
    doc/websocket_user/websocket_user_doc
    doc/grpc_user/grpc_user_doc
    doc/mqtt_user/mqtt_user_doc
    doc/socket_user/socket_user_doc

.. _en-reporting:

Chapter 5 — Reporting & Observability
=====================================

Generate HTML / JSON / XML / CSV / JUnit / percentile-summary / chart
reports, ship metrics to Prometheus, InfluxDB, OTLP, or Datadog
DogStatsD, and stream live progress to a browser.

.. toctree::
    :maxdepth: 2
    :caption: Reporting

    doc/generate_report/generate_report_doc
    doc/metrics/metrics_doc
    doc/test_record/test_record_doc
    doc/live_dashboard/live_dashboard_doc
    doc/notifiers/notifiers_doc

.. _en-orchestration:

Chapter 6 — Orchestration & Scale
=================================

Run distributed master/worker fleets, share state through the parameter
resolver, gate execution on extracted variables, and steer ramps with
built-in load shapes.

.. toctree::
    :maxdepth: 2
    :caption: Orchestration

    doc/distributed/distributed_doc

.. _en-reliability:

Chapter 7 — Reliability
=======================

Adaptive retry, failure budget / circuit breaker, network conditioner,
and process supervisor — the controls that make unattended CI runs
safe.

.. toctree::
    :maxdepth: 2
    :caption: Reliability

    doc/reliability/reliability_doc

.. _en-recording-data:

Chapter 8 — Recording, Data & Importers
=======================================

Convert real browser traffic (HAR), Postman v2.1 collections, OpenAPI
3.x specs, standalone cURL commands, k6 scripts, and JMeter JMX plans
into runnable action JSON. Persist test records to SQLite, compare
runs over time.

.. toctree::
    :maxdepth: 2
    :caption: Recording, Data & Importers

    doc/har_import/har_import_doc
    doc/importers/importers_doc
    doc/sqlite_persistence/sqlite_persistence_doc

.. _en-auth:

Chapter 9 — Auth
================

OAuth2 token helpers with cache, JWT signing (HS / RS), AWS Signature
v4, and mTLS client-cert support on every HTTP user template.

.. toctree::
    :maxdepth: 2
    :caption: Auth

    doc/auth/auth_doc

.. _en-tooling:

Chapter 10 — Tooling, CLI & Diagnostics
=======================================

Command-line subcommands, the hardened control socket server,
exception hierarchy, plus the editor & CI integrations: linter,
schema, LSP, VS Code extension, GitHub Action, and pre-commit.

.. toctree::
    :maxdepth: 2
    :caption: Tooling

    doc/cli/cli_doc
    doc/socket_server/socket_server_doc
    doc/exception/exception_doc
    doc/editor_integration/editor_integration_doc

.. _en-integrations:

Chapter 11 — Integrations
=========================

The optional GUI and the **Model Context Protocol (MCP)** server that
lets Claude drive LoadDensity.

.. toctree::
    :maxdepth: 2
    :caption: Integrations

    doc/gui/gui_doc
    doc/mcp_claude/mcp_claude_doc

.. _en-reference:

Chapter 12 — API Reference
==========================

Auto-generated Python API reference.

.. toctree::
    :maxdepth: 2
    :caption: Reference

    doc/api_reference/api_reference
