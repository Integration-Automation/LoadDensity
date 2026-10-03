# Per-user parameter isolation

Approved predecessor to asyncio HTTP parity in the testing-platform roadmap.
Execute inline in the existing worktree; the coordinating worker owns shared
documentation, commits, facade changes and final review.

## Contract

`ParameterResolver.fork()` deep-copies variable and session state, while CSV/DB
providers remain shared and synchronize row advancement. `use_resolver(instance)`
selects a resolver for an explicit thread/task/greenlet scope and restores the
previous selection on exit. `get_resolver()` exposes the selected/default instance.
Existing resolver facade and registration functions retain legacy defaults.
`${session.NAME}` and session-scoped extraction use a separate local namespace.
One recursive `resolve(value)` consumes at most one row per referenced source.

## Tasks

- [x] Add failing tests for forks, scopes, concurrent extraction and coherent CSV/DB rows.
- [x] Implement scoped facade, detached variable state and locked shared row providers.
- [x] Wire persistent resolver forks into HttpUser/FastHttpUser/httpx-backed Locust users.
- [x] Verify legacy source registration, scenarios, templates and the full suite.

## Review focus

Do not advance CSV rows for each field, share extracted tokens between users,
leak context selection after errors, or import Locust from parameterization.
Asyncio callers explicitly enter one fork per user; child tasks inheriting a scope
share that selected resolver until they explicitly choose their own fork.

## Execution evidence

The initial eight parameter tests failed on missing fork/scope APIs. Six additional
HTTP integration regressions reproduced token contamination, missing httpx
extraction and missing DB source registration; all pass after user scope wiring.
Two database cleanup regressions verified that connection closure alone retained
the pool; the cached source now disposes its engine on success and query failure.

Cookie storage was created before Locust patched threading under the new lazy
facade. A subprocess reproduced sharing a parent cookie jar across patched users,
and async tasks inherited their parent's jar. Context-local storage now detaches
inherited task owners and preserves the legacy explicit user-ID registry.

Focused verification: 618 parameter, source, scenario and user-template tests
passed, with two optional SQLAlchemy skips. The standalone isolation suite now
has 22 passing tests, including real native-thread concurrency and subprocess
checks proving parameter-only imports load neither Locust nor gevent. The same
22 isolation tests also pass with published ActionCore 0.0.2. Final integrated
verification and completion evidence are recorded in the 2026-10 update log.
