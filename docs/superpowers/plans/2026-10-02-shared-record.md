# Shared request record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publish a stdlib request-record contract and connect APITestka and LoadDensity without breaking legacy consumers.

**Architecture:** ActionCore owns the JSON-safe, versioned contract. Framework adapters feed an explicitly scoped RunContext; existing response returns, record lists and summary fields remain compatible. New consumers are developed against isolated checkouts; release-dependent imports are lazy until the ActionCore release is available.

**Tech Stack:** Python 3.10+, TypedDict, ContextVar, threading locks, SQLite, pytest, Locust, requests and httpx.

**Spec:** `docs/superpowers/specs/2026-10-02-shared-record-design.md`; overall roadmap: `2026-10-02-testing-platform-roadmap.md` in the same directory.

## Global Constraints

- ActionCore dependencies remain empty; it must not import any framework or HTTP client.
- schema_version is integer 1; unknown values, NaN and negative measured values are rejected.
- Existing CLI flags, response return shapes, record lists and summary keys remain supported.
- Adapter outcome preserves each runner's existing judgement; no new status policy in this stage.
- No manual package-version bump. The core release precedes consumer dependency-floor changes.
- Framework source changes, tests, three README languages and architecture contracts ship together.
- Execute inline in isolated feature worktrees; the user approved the spec and explicitly requested implementation.

## Review Focus

- Error response objects can be falsey: retain their status/body rather than treating them as absent.
- Failed requests before a response exists need measured elapsed time and nullable status, not fake zeros.
- Context isolation must survive asyncio task inheritance and synchronous runner boundaries.
- Repeated record IDs with conflicting content must fail; identical retries must not double count.
- SDK release order must not make existing imports fail while only the older ActionCore is installed.

---

### Task 1: ActionCore record contract

**Files:** Create `ActionCore/je_action_core/request_record.py`, `ActionCore/test/test_request_record.py`; modify public exports, three READMEs and `architecture.md`.

**Interfaces:** Produces `RequestRecord`, `RecordError`, `RequestRecordError`, `validate_request_record(record: Mapping[str, object]) -> RequestRecord`, `serialize_request_record(record: Mapping[str, object]) -> str` and `request_record_schema() -> dict[str, object]`.

- [x] Write tests proving missing/version/type/outcome/latency/time/assertion errors are rejected; complete success/failure records round-trip; nested bytes/datetime/timedelta serialize safely without arbitrary-object stringification. Hand-derived fixtures assert status 500 remains 500 and the contract has no client imports.
- [x] Run `D:/Codes/ActionCore/.venv/Scripts/python.exe -m pytest test/test_request_record.py -q`; expect missing-module failure before implementation.
- [x] Implement the TypedDict and validators, JSON conversion and schema in the named module. Keep individual validators focused and the public normalization surface independent of transport.
- [x] Run the new tests and `python -m pytest -q` with the ActionCore interpreter; expect all tests pass. Run static checks for the new module.
- [x] Document the new API and commit the ActionCore stage. Do not publish or change a version by hand.

### Task 2: Run context and LoadDensity legacy adapters

**Files:** Create `LoadDensity/je_load_density/utils/test_record/{run_context,contract}.py`, `LoadDensity/test/test_record_contract.py`.

**Interfaces:** Consumes Task 1. Produces `RunContext(source='loaddensity', phase='load', engine='locust', worker_id=None)`, `RunContext.append(record: Mapping[str, object]) -> bool`, `RunContext.snapshot() -> list[RequestRecord]`, `RunContext.to_json() -> str`, `use_run_context(context)` and `get_run_context()`. Adapter: `from_legacy_record(record, context, outcome) -> RequestRecord`; legacy conversion never creates fake timestamps.

- [x] Test two contexts remain isolated, task-local nesting restores prior contexts, identical IDs deduplicate, conflicting IDs fail, input mutations cannot alter snapshots, and LoadDensity/APITestka legacy fixtures normalize status/time/bytes correctly.
- [x] Run `pytest test/test_record_contract.py -q` with the isolated ActionCore on PYTHONPATH; expect missing-module failure.
- [x] Implement the context/sink and source-specific adapters. Import the new core only when a canonical operation is called; missing API raises a clear upgrade error and does not break legacy imports.
- [x] Run the targeted suite; expect pass including malformed import positions, nullable unknown measurements and credential redaction.
- [x] Keep this task's commit together with Task 3 because its public adapter needs a real runner consumer and user documentation.

### Task 3: Locust and async recording

**Files:** Modify `LoadDensity/je_load_density/wrapper/event/request_hook.py`, `engine/asyncio_engine.py`, `utils/test_record/test_record_class.py`; add `test/test_record_engine_integration.py`; update three READMEs, Sphinx record docs and architecture.

**Interfaces:** Consumes Task 2. Locust reads the active context; `run_async_load(..., run_context=None)` explicitly propagates the selected run to asyncio workers. Canonical records are separate from existing legacy lists.

- [x] Test a Locust response with status 500 and falsey truthiness retains status; async success/status failure/transport failure capture distinct records with real elapsed time; consecutive runs' return summaries exclude prior records; scoped recording leaves legacy report keys unchanged.
- [x] Run integration tests; expect failure on the currently missing context output and contaminated run summaries.
- [x] Route measured request outcomes to the context alongside the existing legacy append. Give run_async_load per-invocation counters and propagate cancellation. Keep existing return request/failure semantics.
- [x] Run new tests, existing asyncio/report/SLA/SQLite tests, then the full LoadDensity suite; expect pass.
- [x] Document opt-in canonical collection and commit the LoadDensity recording stage. Record remaining schema-release coordination in progress.md rather than inventing a released version.

### Task 4: APITestka adapters and recording

**Files:** Create `APITestka/je_api_testka/utils/test_record/contract.py`, `run_context.py`, `test/test_utils/test_record_contract.py`; modify requests/httpx sync/async wrappers and record class; update READMEs, Sphinx and architecture.

**Interfaces:** Same canonical context API as Task 2, with source='apitestka' and phase='functional'; context implementation is shared in ActionCore if it proves reusable rather than copied. `record_response(response_data, request, error, engine, elapsed_ms)` appends only when a context is active.

- [x] Add tests using real local requests/httpx calls and failures; assert native return values and failure pairs remain identical while canonical records retain response information and status. Test recording disabled and context cleanup.
- [x] Run those tests with the isolated core; expect missing-module/API failure.
- [x] Wire a scope-aware capture helper into all three wrappers, including before-response errors and clean_record behavior. Preserve caught-error behavior and record_request_info semantics.
- [x] Run the targeted tests, load bridge tests and full APITestka suite; expect pass. Separately run with released ActionCore to prove existing imports still work.
- [x] Document API and commit this repository independently.

### Task 5: Versioned JSON and SQLite export

**Files:** Modify `LoadDensity/je_load_density/utils/test_record/sqlite_persistence.py`; create `test/test_canonical_persistence.py`; update record/export documentation.

**Interfaces:** Consumes contexts. Produces `persist_canonical_records(database_path: str, context: RunContext) -> str`, `fetch_canonical_records(database_path: str, run_id: str) -> list[RequestRecord]`; existing tables and functions remain unchanged.

- [x] Test empty database and existing legacy database, JSON round-trip, multiple runs, duplicate/conflicting records and rollback on invalid records.
- [x] Run the new test; expect missing-function failure.
- [x] Add separate versioned canonical tables and parameterized transactional writes; never migrate or overwrite legacy data implicitly.
- [x] Run persistence and legacy regression tests; expect pass.
- [x] Document the explicit export APIs and commit the persistence stage.

### Task 6: Cross-project verification and release handoff

**Files:** Contract documentation and test fixtures in the three repositories; LoadDensity progress and update log.

**Interfaces:** All Task 1–5 interfaces and the existing APITestka load subprocess bridge.

- [ ] Exercise both projects against a local service, confirm matching keys/types for success and failures and distinct run IDs; run all changed-repository suites and relevant ActionCore consumers.
- [ ] Check three-language docs, schemas/examples, public exports, static analysis and `git diff --check`.
- [ ] Review the whole branch using the requesting-code-review workflow; repair any substantive issues with regression tests.
- [ ] Prepare concrete feature branches/PRs for core and consumers. Consumer dependency-floor activation waits for the real core release; do not mark that rollout finished beforehand.
- [ ] Finish the shared-record stage, retain remaining roadmap items, and continue to smoke/extras CI rather than ending the overall task.
