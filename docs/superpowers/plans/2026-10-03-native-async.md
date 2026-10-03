# Native async engine implementation plan

Execute the previously approved testing-platform roadmap in the existing isolated
feature worktree. Existing public functions, action shape, report filenames and
summary keys remain compatible.

## Dependencies and boundaries

- Per-user resolver forks/context scopes are a coordinated independent task.
- HTTP execution uses genuine httpx async I/O. HTTP/2 is opt-in and requires h2.
- TLS verify/cert/proxy belong to reusable clients, not individual httpx.request
  keyword arguments. Keep a user-owned client pool keyed by TLS/proxy settings;
  share its cookie jar only within that user. Close every client on exit.
- Locust imports and hook registration occur only when selecting Locust APIs.
- Non-HTTP protocol and unsupported native distributed options must fail preflight
  until a genuine async implementation and worker contract exists. Completing
  HTTP support does not close the full protocol/distributed parity item.

## Steps

1. Prove fresh-process package/native imports preserve socket/threading/TLS and do
   not load Locust/gevent. Replace eager public exports and command imports with
   lazy bindings while preserving all existing names and command registry policy.
2. Add start_test engine dispatch for Python/action/CLI. Retain Locust defaults and
   the awaitable run_async_load positional arguments. Validate capabilities,
   numbers, scenarios/assertion/extractor kinds and transport options before I/O.
3. Implement named HTTP kwargs/assertions/extractors, isolated user cookie/variable
   sessions and coherent data sources. Record every measured attempt, including
   assertion/transport/HTTP failures, in legacy and optional canonical formats.
4. Implement sequence/weighted/conditional scenarios, retries, think time,
   asynchronous token buckets, ramp and stages/spike/soak. Separate per-run counts
   from the compatible legacy record sink; expose start/stop/wait/snapshot through
   a RunHandle and callbacks. Cancellation closes clients/tasks and does not become
   a target failure.
5. Wire per-run summary/SLA/report persistence and engine-neutral metric events.
   Verify real HTTP request shapes, cookie/token isolation, bounded concurrency,
   ramp/shape changes, cancellation during I/O, repeated runs and failed preflight.
6. Update three README languages, Sphinx, architecture section6, outstanding work
   and update logs; run full suite and installed-wheel smoke, review then commit.

## HTTP batch boundary

Steps 1-4 and the per-run summary/canonical-record portion of step5 are implemented.
HTTPX transport and lifecycle regressions verify actual async execution, session/cookie
separation, expected-status assertions, retry classification, malformed preflight,
shape concurrency, worker exceptions and cancellation cleanup. Legacy report actions
remain available. Native metric exporters, all non-HTTP protocols and master/worker
execution stay in progress item16; this batch does not close full parity.
Selecting Locust patches its process scheduler. Use a fresh interpreter for native I/O
after a Locust run; CLI bench and the desktop supervisor provide that isolation.

## Primary references

- https://www.python-httpx.org/api/
- https://www.python-httpx.org/async/
- Existing Locust shape tick helpers define shared stage/spike/soak semantics.
