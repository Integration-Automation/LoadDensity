# Smoke tests and Docker extras implementation plan

Execute inline in the existing isolated feature worktree. The approved roadmap and instruction to start implementation authorize these stages.

## Task 1: Wheel smoke harness

- [x] Create stdlib smoke tests in `test/smoke/`, with a separate local HTTP server process and bounded subprocess timeouts.
- [x] Exercise CLI action execution, real Locust requests, summary/JSON/JUnit output, SQLite and SLA pass/failure behavior. Read generated artifacts independently.
- [x] Exercise the async benchmark, dashboard JSON/SSE and MCP initialization in separate processes. Keep GUI lifecycle checks in the GUI capability probe.
- [x] Run the harness against source and an installed checkout-built wheel, repair actual failures, document and commit.

## Task 2: Dynamic Docker installation matrix

- [ ] Generate base/every-extra/all cells directly from `pyproject.toml`: Python 3.12 for every extra plus base 3.10/3.14 on PRs; all Python 3.10–3.14 versions on schedule.
- [ ] Build the wheel using existing locked build tools. Each cell installs that wheel plus only its selected extra in a fresh Docker image, runs pip check, CLI checks and non-skipping capability probes.
- [ ] Define probes for declared extras: create/use their relevant local SDK or framework capabilities, perform MCP handshake even without dependencies, render charts/PDF and launch Qt offscreen. Fail explicitly if a declared extra lacks a probe.
- [ ] Implement a reusable workflow consumed by stable/dev CI; keep pinned actions, minimum permissions and timeouts. Dev publication waits for these checks.
- [ ] Validate representative base/gui/charts/cloud/protocol cells locally in Docker, then complete the whole representative matrix. Repair installation/API incompatibilities rather than excluding supported cells silently.

## Task 3: Protocol service smoke and handoff

- [ ] Add Compose health-checked representative protocol services and distinguish service integration checks from installation probes.
- [ ] Run smoke tests and affected workflow/security tests; update all README languages, Sphinx, architecture and outstanding-work ledger.
- [ ] Commit and push completed stages. Keep GUI/async lifecycle items open if their broader redesign is needed; continue that roadmap implementation instead of claiming parity prematurely.
