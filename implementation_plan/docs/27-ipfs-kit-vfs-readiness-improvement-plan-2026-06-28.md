# IPFS Kit VFS Readiness Improvement Plan (2026-06-28)

Status: Updated after current submodule validation
Scope: external/ipfs_kit VFS + MCP + integration contracts with ipfs_datasets_py and ipfs_accelerate_py

## 1. Current Baseline

Validated today with targeted suites:
- tests/test_vfs_contract_hardening.py
- tests/test_datasets_metadata_index_contract.py
- tests/test_mcp_vfs_adapter_contract.py
- tests/test_vfs_jsonrpc.py
- tests/test_vfs_mcp_tools.py
- tests/test_vfs_mcp_integration.py

Result: passing in current workspace.

What is already in place:
- Durable sync state persistence and transport restore fallback in VFS.
- Metadata index normalization, lineage, queue/circuit/cache controls in datasets integration.
- MCP tools/list filtering so only executable tool subset is advertised.
- CI workflow gate includes integration-test collection guard and execution lane.

## 2. Confirmed Remaining Gaps

### Gap A: Unified MCP runtime lifecycle is still a placeholder
Impact:
- runtime behavior can diverge between test harness and production launch path.
- no real shutdown semantics.

Evidence:
- run() has startup TODO.
- stop() has shutdown TODO.

### Gap B: Duplicate helper method blocks in unified MCP server
Impact:
- drift risk and accidental behavior changes because later definitions shadow earlier ones.
- auditing and maintenance complexity.

Evidence:
- get_all_configs/get_pin_metadata/get_program_state_data/get_bucket_registry/get_backend_status_data each appear twice in unified_mcp_server.py.

### Gap C: VFS accelerate hook is model-discovery only
Impact:
- useful for capability metadata, but not sufficient for index build acceleration by itself.
- actual embedding acceleration happens in datasets manager, so VFS metadata enrichment and datasets enrichment are not explicitly coordinated as one contract.

Evidence:
- ipfs_fsspec _enrich_metadata_with_accelerate calls discover/search/list model operations, not embedding generation.

### Gap D: Double enrichment risk and unnecessary compute
Impact:
- mutation path can trigger accelerate-related work in both VFS and datasets index path.
- extra latency and repeated model discovery under high write rates.

Evidence:
- VFS mutation integrations invoke _enrich_metadata_with_accelerate.
- datasets index path invokes _accelerate_enrich_index.

### Gap E: Async enrichment queue is in-memory only
Impact:
- pending queued enrichment jobs are dropped on crash/restart.
- eventual index completeness depends on process uptime.

Evidence:
- queue is process-local queue.Queue with background thread; no durable queue backing.

### Gap F: Sync snapshot persistence has no retention/compaction policy
Impact:
- sync state and snapshots can grow over time without automatic pruning.

Evidence:
- VFS sync state is persisted and loaded but no age/count/size pruning policy is defined.

## 3. Required Integration Contract (VFS -> datasets -> accelerate)

This is the contract to lock and enforce in code/tests.

### 3.1 VFS to ipfs_datasets_py metadata calls
For each mutation event: write, copy, move, mkdir, rmdir, sync_to_ipfs, sync_from_ipfs, remove/unmount.

Required payload fields:
- schema_version
- operation_id
- operation
- path
- backend
- mount_point
- timestamp
- cid (when applicable)
- source_operation_id and source_cid (when applicable)

Call order:
1. record_ipfs_operation(payload)
2. refresh_metadata_index(path=..., cid=..., operation=..., metadata=payload)
3. update_metadata_index(...) as compatibility fallback
4. store(local_path, metadata=payload) only when local_path exists and is intended
5. event_log append as last-resort fallback

### 3.2 ipfs_datasets_py to ipfs_accelerate_py enrichment calls
For index enrichment:
1. discover_embedding_models() or search_models("embedding") for model availability cache.
2. create_embeddings([text]) preferred for batching.
3. create_embedding(text) fallback.
4. strict timeout + bounded retries + circuit breaker + queue backpressure.
5. persist accelerate_status and timing per index entry.

### 3.3 Division of responsibility
- VFS layer: emit mutation events and lineage envelope; avoid heavy embedding work.
- Datasets layer: own embedding generation and index enrichment lifecycle.
- Accelerate layer: provide model discovery + embedding APIs with stable interface contract.

## 4. Comprehensive Improvement Plan

## Phase 0: Contract Freeze and Interface Adapters (1-2 days)
Tasks:
- Introduce explicit adapter interfaces:
  - DatasetsNotifierAdapter for VFS side.
  - AccelerateEmbeddingAdapter for datasets side.
- Replace broad hasattr fallback trees with explicit capability negotiation and version tags.
- Add contract docs for required/optional fields and error codes.

Definition of done:
- one stable typed interface for datasets notifications and accelerate enrichment.
- compatibility shims still supported but isolated.

## Phase 1: MCP Runtime Productionization (2-4 days)
Tasks:
- Implement real run()/stop() lifecycle or clearly remove unused runtime path.
- Remove duplicate helper method definitions in unified server.
- Add tests asserting one canonical implementation per helper.

Definition of done:
- no TODO placeholders in runtime lifecycle methods.
- duplicate method blocks removed.

## Phase 2: VFS Integration Responsibility Tightening (2-4 days)
Tasks:
- Make VFS accelerate hook optional and metadata-only by default.
- Add config switch to disable VFS-side accelerate enrichment when datasets-side embedding enrichment is active.
- Add per-operation latency metrics around datasets notification path.

Definition of done:
- no duplicate expensive enrichment on common mutation path.
- predictable write latency under load.

## Phase 3: Durable Enrichment Queue (3-6 days)
Tasks:
- Move async enrichment queue from in-memory thread queue to durable queue (file-backed or sqlite-backed).
- Add replay/recovery on startup.
- Add dead-letter tracking for repeatedly failing items.

Definition of done:
- restart does not lose pending enrichment tasks.
- queue health and lag observable.

## Phase 4: Sync State Retention and Integrity (2-4 days)
Tasks:
- Add retention controls for sync snapshots: max entries, max age, max bytes.
- Add periodic compaction/pruning.
- Add integrity verification on restore against manifest hashes where possible.

Definition of done:
- bounded state growth and deterministic restore integrity behavior.

## Phase 5: End-to-End Integration with Real Dependencies (3-5 days)
Tasks:
- Add integration lane that runs against real ipfs_datasets_py and ipfs_accelerate_py environments (not only fakes/mocks).
- Add realistic dataset indexing benchmark scenario:
  - N files
  - index build latency
  - embedding throughput
  - cache hit ratio
- Add performance budget assertions.

Definition of done:
- measurable evidence that index build and inference-prep path perform within agreed SLOs.

## Phase 6: Release Gates and Operational Readiness (1-2 days)
Tasks:
- Keep current contract test lane and add:
  - durable queue recovery tests
  - retention policy tests
  - real-dependency integration smoke
- Add runbook covering degraded modes (datasets unavailable, accelerate unavailable, queue saturation).

Definition of done:
- release blocked if any contract or readiness gate fails.

## 5. Recommended Execution Order (Next Sprint)

1. MCP runtime productionization + duplicate method cleanup.
2. Interface adapter freeze for datasets and accelerate contracts.
3. Disable duplicate heavy enrichment paths by default.
4. Durable enrichment queue implementation.
5. Sync retention controls.
6. Real dependency integration/performance lane.

## 6. Success Criteria

- All VFS mutation events produce consistent lineage-enriched metadata index updates.
- Index enrichment survives restart and catches up reliably.
- Accelerate calls are batched/cached and stay within timeout budgets.
- MCP runtime path used in production has complete start/stop behavior.
- CI demonstrates both correctness and operational readiness, not only unit-contract conformance.
