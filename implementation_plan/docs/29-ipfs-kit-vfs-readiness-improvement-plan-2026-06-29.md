# IPFS Kit VFS Readiness Improvement Plan (2026-06-29)

Status: Core Sprint A/B/C implementation completed and validated in current workspace
Scope: external/ipfs_kit/ipfs_kit_py virtual filesystem and integration contracts with external/ipfs_datasets/ipfs_datasets_py and ipfs_accelerate_py

## 1. Executive Summary

The VFS contract surface is substantially hardened and current focused suites are green, but there are still readiness gaps around ownership boundaries, strictness, and long-term compatibility.

Current strengths:
- Canonical VFS operations are centralized in ipfs_fsspec VFSCore and exposed through sync/async-safe wrappers.
- VFS emits mutation envelopes and calls datasets notifier adapters with compatibility fallback order.
- Datasets metadata manager has lineage normalization, async enrichment queue worker, circuit breaker, and queue persistence/replay metrics.
- Unified MCP server now filters tool listing to executable tools and emits structured errors for non-executable tools.

Primary remaining risk themes:
- Duplicate enrichment responsibilities between VFS and datasets.
- Missing strict validation/integrity checks in restore and conflict-policy configuration.
- Adapter coupling to upstream schema details in queue persistence path.
- Missing real-dependency performance gates for index build throughput.

Execution status:
- Phase 0: complete
- Phase 1: complete
- Phase 2: complete
- Phase 3: complete
- Phase 4: complete
- Phase 5: open, optional cleanup only

## 2. Confirmed Baseline (What Works Today)

Validated by current focused suites in external/ipfs_kit/tests:
- test_vfs_contract_hardening.py
- test_datasets_metadata_index_contract.py
- test_mcp_vfs_adapter_contract.py
- test_vfs_jsonrpc.py
- test_vfs_mcp_tools.py
- test_vfs_mcp_integration.py

Key implemented behaviors:
- VFS sync snapshots persist to disk and support retention by max count and max age.
- VFS mutation integrations emit structured metadata and attempt datasets notification with fallback order.
- Datasets async enrichment supports asyncio/trio backend selection, restart, stop/drain, replay counters, dead-letter counters, and optional DuckDB export to Parquet/CAR.
- Unified MCP server only lists executable tools and returns tool_not_executable for compatibility-only registrations.

## 3. Gap Analysis (Ordered by Severity)

### Critical

1) Enrichment ownership is still duplicated.
- VFS calls accelerate discovery on each mutation path while datasets manager also owns embedding enrichment for index entries.
- This can inflate write-path latency and duplicate model lookup work.

2) Mutation lineage contract is not fully enforced at VFS boundary.
- VFS emits operation_id but source_operation_id/source_cid are not consistently present for transition operations.
- Datasets manager supports these fields, but upstream emission is not strict.

### High

3) Conflict-policy config does not fail fast.
- Unknown policy values currently fall back to overwrite behavior.
- Misconfiguration can silently change data safety semantics.

4) Sync restore integrity is not strictly verified against prior manifest hash.
- Transport restore reconstructs a snapshot, but sync_from_ipfs does not require a strict hash match against stored state before applying restore.

5) Queue persistence path depends on TaskQueue internal table schema.
- The adapter queries tasks table columns directly when TaskQueue backend is used.
- Upstream schema drift in ipfs_datasets_py could break replay/count/export behavior.

### Medium

6) Queue semantics around in-flight/running tasks lack reclaim timeout policy.
- Replayed pending currently includes queued and running statuses.
- No lease timeout/reaper for stale running tasks after abrupt process death.

7) Tool registration surface still includes many compatibility tools in defaults.
- tools/list filters to executable subset, but broad compatibility registration remains and raises maintenance complexity.

### Low

8) VFS integration paths are healthy but spread across multiple legacy servers.
- Canonical server is cleaner now; legacy adapters still increase change-surface and test burden.

## 4. Required Cross-Library Call Contract

## 4.1 VFS to ipfs_datasets_py (metadata/index maintenance)

For operations:
- write, copy, move, mkdir, rmdir, sync_to_ipfs, sync_from_ipfs, mount/unmount when state changes are semantically relevant

Required payload keys:
- schema_version
- operation_id
- operation
- path
- backend
- mount_point
- timestamp
- cid (when known)
- source_operation_id (for derived events)
- source_cid (for derived events)
- entry_count/restored_count/skipped_count when sync operations apply

Call order (strict preference):
1. record_ipfs_operation(payload)
2. refresh_metadata_index(path=..., cid=..., operation=..., metadata=payload)
3. update_metadata_index(...) compatibility alias
4. store(local_path, metadata=payload) only when explicitly intended and local materialization exists
5. event_log append fallback

Response contract expected by VFS caller:
- attempted
- success
- mode
- adapter
- fallback_order

## 4.2 ipfs_datasets_py to ipfs_accelerate_py (index inference acceleration)

Required capability order:
1. discover_embedding_models() else search_models("embedding")
2. create_embeddings([text]) preferred for batch
3. create_embedding(text) fallback
4. timeout budget + retry budget + queue backpressure + circuit breaker
5. persist per-entry accelerate_status and timing

Operational constraints:
- Datasets layer should be sole owner of embedding generation for metadata index.
- VFS layer should only enrich with lightweight capability metadata when explicitly enabled.

## 4.3 Recommended ownership split

- VFS: event emission, lineage envelope, sync context fields.
- Datasets manager: index persistence, queueing/replay/dead-letter, embedding enrichment orchestration.
- Accelerate: model discovery and embedding computation APIs.

## 5. Comprehensive Improvement Roadmap

## Phase 0: Contract Freeze (1-2 days)

Deliverables:
- Publish one versioned contract fixture for VFS->datasets and datasets->accelerate payload/response.
- Add strict envelope validator in VFS before notifier dispatch.
- Add compatibility-version marker to adapter responses.

Definition of done:
- Shared fixture used by VFS and datasets contract tests.

## Phase 1: Enrichment Ownership De-duplication (2-4 days)

Deliverables:
- Set VFS accelerate mode default to lightweight/off for mutation path when datasets async enrichment is enabled.
- Keep optional discovery-only probe behind explicit config.
- Add tests ensuring write path does not perform heavy accelerate calls when datasets enrichment is active.

Definition of done:
- Single-owner enrichment policy enforced and measured.

## Phase 2: Strictness and Integrity Hardening (2-4 days)

Deliverables:
- Validate IPFS_KIT_SYNC_CONFLICT_POLICY at startup; allow only overwrite|skip|strict.
- Add strict restore mode to verify state manifest_hash before apply.
- Add tests for invalid policy and hash mismatch handling.

Definition of done:
- Misconfiguration fails fast and restore integrity behavior is deterministic.

## Phase 3: Queue Durability Compatibility Hardening (2-4 days)

Deliverables:
- Replace direct tasks-table SQL assumptions with a dedicated queue-store adapter abstraction.
- Add schema compatibility checks against ipfs_datasets_py TaskQueue backend.
- Add stale-running reclaim policy (lease timeout/reaper) and tests.

Definition of done:
- Restart/replay behavior is robust to upstream schema evolution and crash recovery edge cases.

## Phase 4: Real Dependency E2E and Throughput Gates (3-6 days)

Deliverables:
- Add CI lane with real ipfs_datasets_py and ipfs_accelerate_py integration.
- Add benchmark scenario for index build:
  - mutation rate
  - queue lag
  - embedding throughput
  - cache hit ratio
  - dead-letter rate
- Define SLO thresholds and fail CI on regressions.

Definition of done:
- Evidence-backed readiness for index-building throughput.

## Phase 5: Legacy Surface Reduction (2-3 days)

Deliverables:
- Keep unified MCP server canonical and isolate or de-scope legacy server paths.
- Minimize compatibility tool registration set to reduce drift.
- Keep adapter contract tests on legacy paths until retirement is complete.

Definition of done:
- Smaller operational surface and lower drift risk.

## 6. Test Plan Additions (Must Add)

1. VFS lineage completeness test:
- assert source_operation_id/source_cid are emitted for copy/move/sync-derived events.

2. Single-owner enrichment test:
- assert no per-mutation accelerate heavy call when datasets async enrichment is enabled.

3. Conflict policy validation test:
- assert unknown policy fails initialization and does not default silently.

4. Restore integrity strict-mode test:
- assert mismatch between stored manifest_hash and restored snapshot rejects apply.

5. Queue adapter compatibility test:
- assert replay/count/export continue functioning with TaskQueue-backed storage contract.

6. Running-task reclaim test:
- assert stale running tasks are re-queued or dead-lettered after lease timeout.

## 7. Operational Readiness Checklist

- Queue telemetry exported: pending_count, dead_letter_count, replayed_count, failure_count, lag.
- Enrichment ownership documented: VFS lightweight only, datasets heavy compute owner.
- Degraded-mode runbook:
  - datasets unavailable
  - accelerate unavailable
  - queue saturation/dead-letter growth
- Performance evidence attached to release sign-off.

## 8. Immediate Next Actions

1. Keep Phase 5 legacy-surface reduction scoped and optional.
2. Roll forward the readiness evidence artifact with contract and benchmark outputs in release automation.
3. Re-run the readiness evidence lane when dependency versions or queue semantics change upstream.

## 9. Concrete Integration Call Map

This section defines the exact call sites and intended target methods so implementation stays consistent.

## 9.1 VFS mutation call map (ipfs_fsspec VFSCore)

Primary emitter:
- VFSCore._run_content_mutation_integrations

Mutation operations currently routed through emitter:
- write
- copy
- move
- mkdir
- rmdir
- sync_to_ipfs
- sync_from_ipfs

Datasets notifier route (in order):
1. manager.record_ipfs_operation(payload)
2. manager.refresh_metadata_index(path=..., operation=..., metadata=payload)
3. manager.update_metadata_index(path=..., operation=..., metadata=payload)
4. manager.store(local_path, metadata=payload)
5. manager.event_log.append(payload)

Required improvement:
- Before route execution, enforce payload validator with required fields and operation-specific required fields.
- For copy/move/sync-derived operations, enforce source_operation_id and source_cid when available.

## 9.2 Datasets index enrichment call map (ipfs_datasets_integration manager)

Enrichment owner:
- IPFSDatasetsManager._accelerate_enrich_index

Discovery route:
1. accelerate.discover_embedding_models()
2. accelerate.search_models("embedding")

Embedding route:
1. accelerate.create_embeddings([text])
2. accelerate.create_embedding(text)

Queue execution route:
- enqueue: _enqueue_enrichment
- worker: _queue_worker_main -> _process_queued_enrichment
- retry/dead-letter: retry_budget and _queue_store_move_to_dead_letter
- lifecycle: _start_queue_worker, stop_async_enrichment, close

Required improvement:
- Lease/reclaim policy for stale running tasks.
- Adapter abstraction that avoids hard-coding task-table assumptions.

## 9.3 VFS accelerate discovery route policy

Current route:
- VFSCore._enrich_metadata_with_accelerate

Policy update:
- When datasets async enrichment is enabled, VFS route should run in lightweight mode only (or disabled) by default.
- Heavy embedding generation remains datasets-only.

## 9.4 Sync durability and integrity route

Current route:
- sync_to_ipfs captures manifest and snapshot blobs
- sync_from_ipfs applies snapshot or transport-restored snapshot

Required improvement:
- Strict restore mode must verify stored manifest_hash matches restored payload hash before apply.
- Invalid conflict-policy config must fail initialization instead of defaulting to overwrite.

## 10. Work Breakdown Structure (Execution Plan)

## Sprint A (Contract and Ownership)

A1. Add contract fixture and validator
- Deliverable: versioned payload schema fixture with required/optional fields.
- Files: ipfs_fsspec mutation integration path, tests fixtures.

A2. Enrichment ownership toggle
- Deliverable: default VFS accelerate mode becomes lightweight/off when datasets async enrichment is active.
- Files: ipfs_fsspec integration mode logic and observability fields.

A3. Coverage for ownership and lineage
- Deliverable: tests for no duplicate heavy enrich calls and lineage field presence.

Exit criteria:
- Write-path mutation tests prove single-owner enrichment policy.

## Sprint B (Strictness and Queue Robustness)

B1. Strict policy validation
- Deliverable: startup/config validation for conflict policy values.

B2. Strict restore integrity mode
- Deliverable: restore rejects mismatched manifest hashes in strict mode.

B3. Queue adapter abstraction
- Deliverable: single queue-store interface with backend adapters.

B4. Stale-running task reclaim
- Deliverable: running-task lease timeout and reclaim/dead-letter behavior.

Exit criteria:
- Crash/restart and stale-task scenarios are deterministic and tested.

## Sprint C (Real dependency and performance readiness)

C1. Real dependency CI lane
- Deliverable: CI job with real ipfs_datasets_py and ipfs_accelerate_py integration tests.

C2. Throughput benchmark lane
- Deliverable: benchmark script and thresholds for mutation-to-index latency and queue lag.

C3. Release readiness report
- Deliverable: generated evidence artifact with pass/fail for contract and performance SLO gates.

Exit criteria:
- CI fails on contract drift or throughput regression beyond thresholds.

## 11. CI Gate Matrix

Always-on contract gates:
- external/ipfs_kit/tests/test_vfs_contract_hardening.py
- external/ipfs_kit/tests/test_datasets_metadata_index_contract.py
- external/ipfs_kit/tests/test_mcp_vfs_adapter_contract.py
- external/ipfs_kit/tests/test_vfs_jsonrpc.py
- external/ipfs_kit/tests/test_vfs_mcp_tools.py
- external/ipfs_kit/tests/test_vfs_mcp_integration.py

New required gates:
- Lineage completeness suite
- Enrichment ownership suite
- Conflict-policy strict validation suite
- Restore integrity strict mode suite
- Queue reclaim/replay robustness suite

Performance gates:
- index_build_p50_ms
- index_build_p95_ms
- queue_lag_p95_ms
- dead_letter_rate
- embedding_cache_hit_ratio

## 12. Go/No-Go Readiness Criteria

Go criteria:
1. All contract suites and new strictness suites pass.
2. Real dependency lane passes without fallback-only behavior.
3. Performance SLO thresholds pass in two consecutive CI runs.
4. Degraded-mode runbook validated by smoke scenarios.

No-go criteria:
1. Any fallback-only path silently replacing canonical call path in CI.
2. Strict restore mismatch accepted under strict mode.
3. Unknown conflict policy accepted at startup.
4. Queue replay or reclaim behavior loses jobs under restart simulation.

## 13. Tracking and Ownership

Recommended tracking fields for each work item:
- owner
- target sprint
- code paths touched
- tests added
- benchmark delta
- rollout risk

Recommended weekly status rollup:
- Contract status: green/yellow/red
- Queue durability status: green/yellow/red
- Performance gate status: green/yellow/red
- Remaining blockers and mitigation owner
