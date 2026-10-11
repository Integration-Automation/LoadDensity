# Distributed Health Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this approved plan task by task.

**Goal:** Fail unhealthy startup, observe worker lifecycle, and reuse Locust redistribution with deterministic cleanup.

**Architecture:** Configure Locust native heartbeat constants in a scoped process lease and enable native rebalancing. Observe public event hooks and runner client state; do not introduce a heartbeat sender or user allocator. Own auxiliary greenlets and RPC cleanup at the environment boundary.

**Tech Stack:** Python 3.10+, gevent, installed Locust 2.43.4; official stable source inspected at 2.46.6.

**Spec:** ../specs/2026-10-02-testing-platform-roadmap.md, distributed health section.

## Constraints

- Defaults: worker_startup_timeout=60, worker_heartbeat_interval=5, worker_lost_timeout=15; finite positive values, lost timeout greater than interval.
- Only healthy ready workers satisfy expected_workers. Default startup policy fails and cleans up; explicit degraded policy requires at least one healthy ready worker.
- Redistribute virtual-user capacity using Locust at the existing target and spawn rate; never replay HTTP requests or migrate sessions.
- Locust heartbeat constants are process scoped. Matching concurrent configurations share a lease; conflicting configurations fail before creating a runner. Restore previous constants after final cleanup.
- Finite work shards are not supported by this wrapper. Do not advertise exactly-once requests, finite-work leases, or request-result deduplication.
- Root owns shared README, Sphinx, architecture, progress, update logs, and commits.

## Tasks

- [x] Add failing tests for configuration validation, readiness, startup timeout/degraded policy, and scoped settings.
- [x] Add native configuration scope and observable worker lifecycle; make the startup gate fail by default.
- [x] Add failing native-message tests for loss, reconnection, all lost, capacity shortfall, ramp, shapes, and cleanup.
- [x] Enable native rebalancing and preserve target/ramp while exposing health and affected worker journeys.
- [x] Add cooperative stop_requested and on_environment hooks; test callback order and cancellation cleanup.
- [x] Run focused tests and report verification evidence and limits to the root for shared documentation.

## References

- https://docs.locust.io/en/stable/_modules/locust/runners.html
- https://docs.locust.io/en/stable/api.html#event-hooks
- https://docs.locust.io/en/stable/configuration.html

## Timing and capacity limits

Native heartbeat checks occur on interval ticks; lost detection is quantized to that interval. All nodes in a distributed run must use matching timing settings. Missing/reconnected workers may interrupt stateful journeys; rebalanced users begin fresh sessions. Health distinguishes worker availability from target HTTP health. Native worker CPU warnings and reported user counts expose inadequate capacity; workers do not declare a hard user-capacity limit. Finite work assignment and canonical distributed request aggregation remain separate future work.

## Delivered API

`start_test` and `prepare_env` accept the worker settings through existing keyword arguments. Master results include `distributed_health`; an active master exposes `env.distributed_health.snapshot()` with worker states, target and reported users, affected worker identifiers, session continuity disclosure, and request replay disabled. A lost worker remains observable until native Locust removal or master cleanup; reconnection uses native dispatch bookkeeping.

`on_environment(env)` runs in the calling execution thread before readiness/start. `stop_requested()` is checked during startup and polled every 50ms during execution. `prepare_env` closes owned runner, telemetry/timer/cancellation greenlets, UI, and RPC resources on return/error. Direct `create_env` callers own the returned environment and must call `cleanup_env(env)`; cleanup is idempotent. Shape factories are instantiated before environment construction and native headless completion terminates the run.

## Verification evidence

- Red: seven initial configuration/scope tests failed against previous behavior; cancellation timed out because its callback was ignored.
- Red: native-state and startup cancellation tests caught premature loss classification and starting after cancellation; shape and cleanup tests caught shape factory misuse, a completion hang, lost degraded status, and UI-stop errors interrupting transport cleanup.
- Green: `test/test_distributed_health.py`: 31 passed, including a real loopback RPC worker plus controlled RPC delivery for deterministic loss/recovery/ramp assertions and callback failures during ramp-up.
- Full suite: `python -m pytest test/ -q` with the project interpreter and ActionCore worktree on `PYTHONPATH`: 1411 passed, 2 skipped, 4 existing warnings in 77.06s. Root performs final verification after concurrent UI/cloud work.
- Owned modules compile and `git diff --check` reports no whitespace errors.

No finite-work assignment option is exposed. Native virtual-user redistribution does not deduplicate HTTP side effects or aggregate canonical request records across workers. Those capabilities require a separate explicit distributed record/shard contract.
