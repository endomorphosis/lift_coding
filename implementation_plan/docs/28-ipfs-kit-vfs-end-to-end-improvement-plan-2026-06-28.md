# IPFS Kit VFS End-to-End Improvement Plan (2026-06-28)

Status: Updated after focused contract validation and async backend migration
Scope: external/ipfs_kit/ipfs_kit_py virtual filesystem and integration contracts with ipfs_datasets_py and ipfs_accelerate_py

## 1. Investigation Summary

Current focused contract suites are passing in this workspace:
- external/ipfs_kit/tests/test_vfs_contract_hardening.py
- external/ipfs_kit/tests/test_datasets_metadata_index_contract.py
- external/ipfs_kit/tests/test_mcp_vfs_adapter_contract.py
- external/ipfs_kit/tests/test_vfs_jsonrpc.py
- external/ipfs_kit/tests/test_vfs_mcp_tools.py
- external/ipfs_kit/tests/test_vfs_mcp_integration.py

Validated baseline behavior includes:
- Durable VFS sync-state persistence with transport restore fallback.
- Adapterized datasets notification and accelerate model-discovery hooks in VFS.
- Dataset metadata index normalization, lineage, async enrichment queue controls.
- AnyIO backend selection for async queue worker (asyncio or trio).
- MCP tools/list filtered to executable surface in unified server.

## 2. Confirmed Remaining Gaps

## Gap A (Critical): Async enrichment queue is not durable across restart

What is missing:
- Queue items are stored in process memory only and are lost on crash/restart.

Evidence:
- Queue is in-memory queue.Queue in external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py.
- No persisted pending-jobs ledger, replay, or dead-letter storage.

Impact:
- Metadata index enrichment can remain permanently incomplete after interruption.

## Gap B (High): Queue cannot be cleanly restarted after stop

What is missing:
- stop_async_enrichment sets the stop event, but worker startup path does not clear it.

Evidence:
- stop_async_enrichment sets self._queue_stop in external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py.
- _start_queue_worker does not reset self._queue_stop before starting thread.

Impact:
- After stop, subsequent worker restarts can no-op or immediately exit.

## Gap C (High): VFS performs accelerate discovery on every mutation while datasets also performs enrichment

What is missing:
- Clear single-owner policy for expensive enrichment work.

Evidence:
- VFS write/mkdir/move/copy/rmdir/sync calls _run_content_mutation_integrations in external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py.
- _run_content_mutation_integrations invokes both _notify_dataset_metadata and _enrich_metadata_with_accelerate.
- datasets refresh path also runs or queues _accelerate_enrich_index in external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py.

Impact:
- Duplicated accelerate-related work and extra latency under write-heavy load.

## Gap D (Medium): Conflict policy is permissive for invalid values

What is missing:
- Strict startup validation for conflict policy values.

Evidence:
- _should_overwrite_content falls back to overwrite for unknown policy values in external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py.

Impact:
- Misconfiguration silently changes behavior and can hide data conflict risk.

## Gap E (Medium): Transport restore success depends on datasets load behavior, no end-to-end integrity check on restore

What is missing:
- Optional manifest hash verification against restored payload after transport load.

Evidence:
- _restore_snapshot_from_transport reconstructs snapshot and manifest hash, but sync_from_ipfs does not verify previously stored manifest hash against restored content for strict mode before applying.

Impact:
- Harder to detect transport/data drift in remote recovery scenarios.

## Gap F (Medium): MCP runtime is stdio-first with limited production transport lifecycle

What is missing:
- Explicit production transport lifecycle or explicit de-scoping for non-stdio runtime.

Evidence:
- unified_mcp_server run() prioritizes stdio and otherwise logs no transport configured.

Impact:
- Deployment ambiguity for production serving modes.

## 3. Required End-to-End Call Contract

## 3.1 VFS to ipfs_datasets_py mutation contract

For mutation operations:
- write
- copy
- move
- mkdir
- rmdir
- sync_to_ipfs
- sync_from_ipfs
- remove/unmount where applicable

Required envelope fields:
- schema_version
- operation_id
- operation
- path
- backend
- mount_point
- timestamp
- cid (when present)
- source_operation_id and source_cid (for lineage transitions)

Required call precedence:
1. record_ipfs_operation(payload)
2. refresh_metadata_index(path=..., cid=..., operation=..., metadata=payload)
3. update_metadata_index(...) compatibility alias
4. store(local_path, metadata=payload) only when local materialization exists and this is explicitly intended
5. event_log append as final fallback

Result contract:
- VFS operation result includes integration.dataset containing:
  - attempted
  - success
  - mode
  - adapter
  - fallback_order

## 3.2 ipfs_datasets_py to ipfs_accelerate_py enrichment contract

Discovery and embedding contract:
1. discover_embedding_models() preferred
2. search_models("embedding") fallback
3. create_embeddings([text]) preferred batch embedding
4. create_embedding(text) fallback
5. timeout + retry budget + queue backpressure + circuit breaker

Persistence and observability contract:
- For each indexed item, persist accelerate_status including:
  - attempted
  - success
  - reason or adapter mode
  - timing/error metadata when relevant
- Snapshot metrics include queue, retries, dropped jobs, cache behavior.

## 3.3 Responsibility split

- VFS owns mutation envelope emission and lineage context.
- datasets owns index persistence, queue lifecycle, embedding enrichment.
- accelerate owns model discovery and embedding interfaces.

Design rule:
- VFS accelerate hook defaults to metadata capability probe only.
- datasets performs embedding-heavy work to avoid duplicate compute.

## 4. Comprehensive Improvement Roadmap

## Phase 0: Contract Freeze (1-2 days)

Deliverables:
- Write a single contract reference doc for VFS->datasets and datasets->accelerate fields.
- Add schema validation utility for mutation envelope required keys.
- Add compatibility-version tags for adapters.

Definition of done:
- Contract fixture used by both VFS and datasets tests.

## Phase 1: Queue Lifecycle Correctness (1-2 days)

Deliverables:
- Fix restart semantics by clearing stop event before worker restart.
- Add idempotent start/stop/join behavior tests.
- Add explicit state transitions in queue telemetry.

Definition of done:
- stop/start cycles work repeatedly in same process.

## Phase 2: Durable Queue and Replay (3-6 days)

Deliverables:
- Add persisted pending-job store in DuckDB with optional Parquet export and CAR conversion pipeline.
- Replay pending jobs on startup with dedupe keys.
- Add dead-letter queue for repeatedly failing jobs.

Definition of done:
- Crash/restart preserves pending enrichments and eventual completion.

## Phase 3: De-duplicate Enrichment Ownership (2-4 days)

Deliverables:
- Introduce config gate to disable VFS-side accelerate discovery when datasets enrichment is enabled.
- Keep optional metadata capability probe, but no heavy repeated model/discovery calls on each write.
- Add latency regression guard for write path.

Definition of done:
- Under mutation load, only one layer performs enrichment compute path.

## Phase 4: Sync Integrity and Policy Validation (2-4 days)

Deliverables:
- Validate IPFS_KIT_SYNC_CONFLICT_POLICY at startup (allow only overwrite|skip|strict).
- Add strict integrity mode for restore hash verification.
- Extend retention controls with max-bytes option and compaction reporting.

Definition of done:
- Invalid policy fails fast.
- Restore can verify integrity before applying content.

## Phase 5: MCP Runtime Clarity (2-3 days)

Deliverables:
- Either implement explicit production transport(s) with lifecycle semantics or document/lock stdio-only runtime scope.
- Add lifecycle tests for run/stop under supported transport mode.

Definition of done:
- Deployment mode is unambiguous and tested.

## Phase 6: Real Dependency E2E and Performance Gates (3-5 days)

Deliverables:
- Add test lane against real ipfs_datasets_py and ipfs_accelerate_py instances.
- Benchmark index build throughput and queue lag under representative dataset mutations.
- Define SLO budgets and CI alert thresholds.

Definition of done:
- CI captures correctness plus throughput/readiness evidence.

## 5. Test Additions Required

Must-add focused tests:
- Queue restart cycle test: start -> stop -> start -> queued job processed.
- Durable replay test: enqueue -> process crash simulation -> restart -> replay succeeds.
- Enrichment ownership test: VFS write path does not duplicate heavy accelerate calls when datasets async enrichment is enabled.
- Invalid conflict policy test: startup/config load fails on unknown value.
- Strict restore integrity mismatch test: restore rejects tampered payload when strict integrity enabled.

## 6. Operational Readiness Checklist

- Queue lag and dead-letter counts exported in metadata snapshot and monitoring.
- Recovery runbook for datasets unavailable / accelerate unavailable / queue saturation.
- Versioned contract for mutation envelope rolled out with backward-compatible parsing.
- Performance evidence artifact attached to release process.

## 7. Recommended Next Execution Steps

1. Implement queue restart fix and tests (Phase 1).
2. Implement durable queue + replay + dead-letter semantics (Phase 2).
3. Enforce single-owner enrichment policy and measure write latency reduction (Phase 3).
4. Add conflict policy validation and strict restore integrity mode (Phase 4).
5. Run real-dependency E2E benchmark lane before release sign-off (Phase 6).
