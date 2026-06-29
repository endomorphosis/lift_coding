# IPFS Kit VFS Gap Analysis And Improvement Plan

Status: Proposed
Date: 2026-06-28
Scope: external/ipfs_kit with integration contracts to external/ipfs_datasets and external/ipfs_accelerate

## Executive Summary

The VFS core has meaningful progress (durable sync state, metadata envelope standardization, dataset/accelerate hooks, conflict policies), but there are still production-readiness gaps that can cause behavioral drift, weak MCP guarantees, and incomplete end-to-end sync semantics.

Highest-risk open issues:
1. Unified MCP still advertises non-VFS tools that route to generic not_implemented responses.
2. VFS sync uses dataset-backed storage as best effort but does not guarantee remote pull semantics for restore across process/host boundaries.
3. A key integration test file defines methods that pytest does not collect because class naming does not follow pytest discovery patterns.
4. Legacy daemon-mgmt server file still carries duplicate constructor definitions, increasing drift risk.

## Current Verified Integration Paths

### VFS to ipfs_datasets_py (via IPFSDatasetsManager wrapper)

Observed in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py):
- Primary path: `record_ipfs_operation(payload)`
- Fallbacks: `refresh_metadata_index(...)`, `update_metadata_index(...)`, `store(local_path, metadata=...)`, append to `event_log`

Observed manager API in [external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py](external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py):
- `record_ipfs_operation(payload)`
- `refresh_metadata_index(path, cid, operation, metadata)`
- `update_metadata_index(...)` alias
- `remove_from_metadata_index(path|cid, tombstone=...)`
- `list_metadata_index()`, `metadata_index_snapshot()`

### VFS to ipfs_accelerate_py

Observed in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py):
- `discover_embedding_models()` preferred
- fallback `search_models("embedding")`
- fallback class path `AccelerateCompute.discover_embedding_models/search_models/list_models`

Observed index-build acceleration in [external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py](external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py):
- model discovery cache
- embedding cache with optional batch call via `create_embeddings([text])`
- per-item fallback `create_embedding(text)`
- queue/backpressure/circuit-breaker metrics

## Findings (Ordered By Severity)

### Critical

1. Advertised-vs-executable MCP mismatch still exists for many non-VFS tools.
- Evidence: [external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py#L77), [external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py#L575), [external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py#L612)
- Impact: clients can discover tools that cannot execute, producing runtime contract failures.

2. End-to-end remote sync restoration is not fully guaranteed.
- Evidence: transport push is best effort in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py#L2352), but restore still depends on local persisted snapshot state in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py#L2956)
- Impact: restart-safe on one host, but not necessarily portable/remote-fetch capable for CID-only recovery.

### High

3. Integration test file is effectively non-running under pytest collection.
- Evidence: class is named `MCPVFSIntegrationTest` rather than pytest-discoverable `Test...` in [external/ipfs_kit/tests/test_vfs_mcp_integration.py](external/ipfs_kit/tests/test_vfs_mcp_integration.py#L34)
- Impact: false confidence from green matrix while this file collects 0 tests.

4. Legacy daemon-mgmt server has duplicate constructor definitions.
- Evidence: duplicate `__init__` in [external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_mcp_server_with_daemon_mgmt.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_mcp_server_with_daemon_mgmt.py#L879) and [external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_mcp_server_with_daemon_mgmt.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_mcp_server_with_daemon_mgmt.py#L2192)
- Impact: maintainability and future guard regressions.

### Medium

5. Async enrichment worker lifecycle is incomplete.
- Evidence: worker start exists in [external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py](external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py#L485), but no public shutdown/join or drain API.
- Impact: long-running process resource leakage and difficult deterministic test teardown.

6. Sync state file growth lacks retention controls.
- Evidence: persisted snapshots accumulate in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py#L1921) with no pruning/TTL.
- Impact: unbounded local disk growth.

7. Conflict policy input is permissive and not validated.
- Evidence: value is read from env in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py#L1890) and defaults to overwrite semantics for unknown policy.
- Impact: silent misconfiguration.

### Low

8. Duplicate utility methods in unified server increase drift probability.
- Evidence: repeated helper method blocks in [external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py)
- Impact: maintenance overhead.

## Target Contract: Required Call Matrix

### Mutation Events (VFS to datasets)

For operations `{write, copy, move, mkdir, rmdir, sync_to_ipfs, sync_from_ipfs, remove, unmount}` VFS should emit:
- `schema_version`
- `operation_id`
- `operation`
- `path`
- `backend`
- `mount_point`
- `timestamp`
- Optional lineage keys: `cid`, `source_cid`, `source_operation_id`

Execution order:
1. Attempt `record_ipfs_operation(payload)`
2. Fallback `refresh_metadata_index(...)`
3. Fallback `update_metadata_index(...)`
4. Fallback `store(local_path, metadata=payload)` where applicable
5. Fallback append to `event_log`

### Index Enrichment (datasets to accelerate)

For each index entry:
1. Resolve embedding model catalog:
- `discover_embedding_models()` else `search_models("embedding")`
2. Resolve vectors:
- Prefer `create_embeddings([text])` when available
- Fallback `create_embedding(text)`
3. Enforce timeout, retry budget, queue backpressure, circuit breaker.
4. Persist enrichment status and metrics into metadata snapshot.

## Improvement Plan

## Phase 0: Test And Contract Integrity (1-2 days)

Tasks:
- Rename/reshape integration tests to ensure pytest collection in [external/ipfs_kit/tests/test_vfs_mcp_integration.py](external/ipfs_kit/tests/test_vfs_mcp_integration.py)
- Add explicit test that fails when collection count is zero for designated suites.
- Add tests asserting advertised-vs-callable parity for non-VFS MCP tools.

Definition of done:
- Integration suite collects and runs tests.
- CI fails if expected suites collect zero tests.

## Phase 1: Unified MCP Tool-Surface Correctness (2-4 days)

Tasks:
- For all names in DEFAULT_TOOL_NAMES, either:
  - implement callable handlers, or
  - remove from list/tools registration.
- Keep small compatibility stubs only for clearly documented tools.
- Add strict parity checker in CI: `tools/list` names must have executable path.

Definition of done:
- No `code=not_implemented` for advertised tools.

## Phase 2: Remote-Capable Sync Semantics (4-7 days)

Tasks:
- Add transport abstraction layer in VFS:
  - `deterministic`
  - `datasets_store`
  - optional direct IPFS daemon/gateway pin/add/get
- Persist minimal manifest metadata for CID-only restore.
- Implement restore path that can fetch from remote transport when local snapshot missing.
- Add snapshot retention policy (count/age/size based pruning).

Definition of done:
- `sync_from_ipfs` can recover by CID without requiring local snapshot cache.

## Phase 3: Metadata Envelope And Lifecycle Hardening (2-4 days)

Tasks:
- Enforce strict validation for required payload fields before dataset dispatch.
- Add tombstone retention policy and compaction job.
- Add strict config validation for sync conflict policy values.

Definition of done:
- Invalid policy/config is explicit error at startup.
- Index remains bounded and deterministic under churn.

## Phase 4: Accelerate Throughput And Operability (3-5 days)

Tasks:
- Add worker lifecycle API: start/stop/join/drain for async enrichment queue.
- Add batch-size tuning and queue latency metrics.
- Add fast-fail behavior when accelerate is unavailable for prolonged windows.
- Add benchmark suite for index build throughput.

Definition of done:
- Stable throughput with bounded memory/queue under stress.
- Deterministic shutdown in tests and production.

## Phase 5: Legacy Surface De-risking (1-3 days)

Tasks:
- Remove duplicate constructor definitions in daemon-mgmt legacy server.
- Isolate legacy modules behind explicit compatibility package.
- Ensure production guard behavior tested once at integration boundary.

Definition of done:
- No duplicate critical lifecycle methods in legacy modules.

## Phase 6: CI And Release Gates (1-2 days)

Tasks:
- Add contract lane that runs:
  - test_vfs_contract_hardening
  - test_datasets_metadata_index_contract
  - test_mcp_vfs_adapter_contract
  - test_vfs_jsonrpc
  - test_vfs_mcp_tools
  - collected-and-run check for test_vfs_mcp_integration
- Add release checklist evidence artifact upload.

Definition of done:
- Release blocked on contract/test collection parity failures.

## Acceptance Criteria

1. All advertised MCP tools execute or are removed from advertisement.
2. VFS sync restore works with CID-only path across restart/host boundary.
3. Metadata index envelope validation is strict and versioned.
4. Accelerate enrichment pipeline remains bounded and observable under load.
5. Integration suites are actually collected and enforced in CI.

## Recommended Immediate Next Actions

1. Fix pytest collection in [external/ipfs_kit/tests/test_vfs_mcp_integration.py](external/ipfs_kit/tests/test_vfs_mcp_integration.py).
2. Implement non-VFS tool parity cleanup in [external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py](external/ipfs_kit/ipfs_kit_py/mcp/servers/unified_mcp_server.py).
3. Add remote restore fallback path in [external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py](external/ipfs_kit/ipfs_kit_py/ipfs_fsspec.py).
4. Add queue lifecycle controls in [external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py](external/ipfs_kit/ipfs_kit_py/ipfs_datasets_integration.py).
