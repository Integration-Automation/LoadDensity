# Distributed Canonical Records Implementation Plan

> Implement the approved aggregate composition and native message protocol using existing lifecycle boundaries.

**Goal:** Deliver canonical worker request results to an explicitly selected master run without changing default legacy execution.

**Architecture:** `DistributedRunContext` composes strict ActionCore contexts per source worker and validates full batches before committing. A native Locust hello/config/ready exchange binds producer epochs to master run identity. Bounded worker queues send a sequenced batch until acknowledged, retaining identical request record identifiers across retries. Master acceptance validates transport identity and projects newly accepted records to legacy reports.

**Constraints:** No ActionCore internals or identity rewriting. Bound record bytes, batch bytes/count, and pending bytes/count. Stale generations, foreign identities, malformed records, conflicting retries and queue overflow are explicit failures. Final drains are bounded; missing acknowledgements remain observable. Ongoing virtual-user capacity redistribution is independent of record delivery. There is no finite work queue, request exactly-once guarantee, or session migration.

## Tasks

- [x] Red/green aggregate identity, global deduplication, JSON conflict and atomic batch tests.
- [x] Red/green bounded producer batching, retries, acknowledgement, generation and failure tests.
- [x] Wire opt-in contexts and sinks into isolated environments, readiness and cleanup.
- [x] Exercise real loopback Locust messages, final drain, cancellation, loss/reconnection and legacy report counts.
- [x] Replace the ramp test's original-dispatcher completion assumption with native final capacity completion.
- [x] Run focused and lint checks; report limitations and exact files to the parent for full-suite integration.

## API

Master selects `run_context=DistributedRunContext(...)`; every worker opts in with `distributed_records=True`. Import the aggregate from `je_load_density.utils.test_record.distributed_context`. Worker limits are provided through existing kwargs. An aggregate exposes `run_id`, `snapshot()`, `to_json()`, and transactional `ingest_batch(worker_id, records)`. Delivery diagnostics are available on `env.record_delivery.snapshot()`. Strict ordinary ActionCore contexts and default legacy environments retain their current behavior. A canonical master counts only workers that have completed both native and canonical readiness; default fail startup prevents load starting with an unbound producer.

| Existing kwargs | Default | Meaning |
|---|---:|---|
| `record_batch_size` | 100 | Maximum records per batch |
| `record_batch_bytes` | 262144 | Maximum UTF-8 JSON bytes for the whole batch envelope |
| `record_max_bytes` | 65536 | Maximum UTF-8 JSON bytes per canonical record |
| `record_max_pending` | 1000 | Maximum queued records, including the in-flight batch |
| `record_pending_bytes` | 4194304 | Maximum queued serialized record bytes |
| `record_flush_interval` | 0.1 | Flush and identical retry interval in seconds |
| `record_drain_timeout` | 2 | Bounded drain and terminal acknowledgement budgets in seconds |

Master bounds are negotiated with each worker using the smaller configured limits. Positive counts and finite positive times are required; an individual record must fit inside the batch and pending byte limits. Queue overflow fails the run without discarding old entries or growing an unbounded retry queue. Queued measurements captured before the handshake are bound once to the authenticated master identity. Each producer assigns UUID record IDs once; reconnects and identical retries preserve them. Record ID conflicts anywhere in a run reject the entire batch.

The master projects only newly accepted canonical records into the existing success/error report lists. Global report percentiles therefore use delivered individual measurements, without averaging per-worker percentiles. Payload capture remains disabled by the existing canonical adapter. SQLite canonical export accepts the aggregate's public `run_id` and detached `snapshot()`.

## Shutdown and limits

Custom handlers use the existing native message channel; no second heartbeat or user dispatcher is added. A final flush stops worker users in an owned auxiliary greenlet, while the native RPC reader remains able to process acknowledgements. Concurrent cleanup waits for the active drain. Worker close also waits for a terminal master acknowledgement before transport closure; pending loss and missing workers fail explicitly. Closed producers ignore late batch acknowledgements, preserving final loss diagnostics.

Terminal control messages enforce exact field sets, a maximum 128-byte UTF-8 nonce, and the configured envelope byte bound. Completion acknowledgements include only protocol fields; incoming data is never reflected wholesale. The sender also refuses oversized or non-serializable outgoing messages. Per-worker session history retains at most 128 retired producer epochs. Retired bootstrap hellos are ignored without changing the active producer or failing its valid traffic. When retirement history reaches capacity, a further replacement fails explicitly without eviction or session mutation, preventing resurrection of old epochs.

This is bounded in-memory transport, not durable recovery: process termination can lose pending records, and the aggregate retains delivered run history in memory until exported. A master restart does not restore its generation/index state. A worker with pending records rejects a different run identity. All canonical workers must opt in; an explicitly degraded mixed startup can still end with incomplete delivery diagnostics. Locust's native load shapes, virtual-user redistribution and stateful session limitations remain independent of record delivery. There is no finite scenario shard queue or lease/retry API in this implementation, and no HTTP request replay, exactly-once execution or session migration guarantee.

## Verification evidence

The initial aggregate tests failed because the module was absent; producer/master tests then exposed missing acceptance and changed in-flight payloads on repeated configuration. Real native cancellation reproduced early RPC closure while another greenlet was draining, and local worker stop reproduced loss of its final completion message. Regressions cover both fixes, retry identity, malformed/foreign batches, stale generations/configuration, byte/count boundaries, reconnects, two-worker provenance, final flush and cleanup. A stalled-send regression verifies that transport retries cannot defeat the drain deadline, and an aggregate SQLite roundtrip preserves worker identity and record deduplication. Cleanup records delivery failures without masking an active caller/callback exception. The 56 aggregation tests and existing health/record regressions are checked with the coordinated ActionCore checkout; Ruff E/F/W/C90/I runs across all six owned Python paths. Controlled health tests bind random ports to permit parallel execution. Parent integration owns the full suite and shared documentation.

Pre-review focused verification: **97 passed** (49 aggregation, 31 health, 17 canonical/engine/legacy record checks) in 24.39 seconds. Ruff E/F/W/C90/I and owned tracked-file whitespace checks passed. Earlier integrated verification also included native import regressions. Existing Locust late monkey-patching and legacy `TestRecord` collection warnings remain.

Final review reproduced six failures: oversized/extra-field DONE messages finalized sessions and reflected payloads, malformed FLUSH/FINISHED controls were accepted, retired bootstrap epochs resurrected, and retirement history had no capacity limit. Those seven new cases (including an already passing normal DONE acknowledgement) now pass. Final follow-up verification: **87 passed** (56 aggregation plus 31 health) in 28.15 seconds; Ruff E/F/W/C90/I and owned-file whitespace checks passed. The canonical suite now calls `pytest.importorskip("je_action_core.request_context")` before importing the LoadDensity adapter, preserving collection compatibility when published ActionCore lacks the optional canonical API. Parent integration verifies the old-core wheel and full suite.

## References

- https://docs.locust.io/en/stable/running-distributed.html#communicating-across-nodes
- https://docs.locust.io/en/stable/api.html#event-hooks
- Installed Locust 2.43.4 public runner message methods and event hooks; current official stable documentation was verified at 2.46.6.
