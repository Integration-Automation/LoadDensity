# Smoke tests and Docker extras implementation plan

Execute inline in the existing isolated feature worktree. The approved roadmap and instruction to start implementation authorize these stages.

## Task 1: Wheel smoke harness

- [x] Create stdlib smoke tests in `test/smoke/`, with a separate local HTTP server process and bounded subprocess timeouts.
- [x] Exercise CLI action execution, real Locust requests, summary/JSON/JUnit output, SQLite and SLA pass/failure behavior. Read generated artifacts independently.
- [x] Exercise the async benchmark, dashboard JSON/SSE and MCP initialization in separate processes. Keep GUI lifecycle checks in the GUI capability probe.
- [x] Run the harness against source and an installed checkout-built wheel, repair actual failures, document and commit.

## Task 2: Dynamic Docker installation matrix

- [x] Generate base/every-extra/all cells directly from `pyproject.toml`: Python 3.12 for every extra plus base 3.10/3.14 on PRs; all Python 3.10–3.14 versions on schedule.
- [x] Build the wheel using existing locked build tools. Each cell installs that wheel plus only its selected extra in a fresh Docker image, runs pip check, CLI checks and non-skipping capability probes.
- [x] Define probes for declared extras: create/use their relevant local SDK or framework capabilities, perform MCP handshake even without dependencies, render charts/PDF and launch Qt offscreen. Fail explicitly if a declared extra lacks a probe.
- [x] Implement a reusable workflow consumed by stable/dev CI; keep pinned actions, minimum permissions and timeouts. Dev publication waits for these checks.
- [x] Validate representative base/cloud/protocol cells locally in Docker, then complete the whole representative matrix including GUI/charts/all in CI. Repair installation/API incompatibilities rather than excluding supported cells silently.

2026-10-03 verification: all 48 Docker installation cells, ten Windows/Ubuntu
Python3.10–3.14 unit-test jobs and the healthy Compose service job passed for
head82912d5 (Actions run37006974442). GUI/all offscreen launch uses the writable
home of the unprivileged account. Full GUI execution/cancellation smoke remains
separately tracked in progress.md #24 until the desktop lifecycle redesign.

## Task 3: Protocol service smoke and handoff

- [x] Add Compose health-checked representative protocol services and distinguish service integration checks from installation probes.
- [x] Run smoke tests and affected workflow/security tests; update all README languages, Sphinx, architecture and outstanding-work ledger.
- [ ] Commit and push completed stages. Keep GUI/async lifecycle items open if their broader redesign is needed; continue that roadmap implementation instead of claiming parity prematurely.
