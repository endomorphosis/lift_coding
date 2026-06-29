# IPFS Kit VFS Integration Task Board

Status: Completed
Scope: external/ipfs_kit submodule, with explicit integration contracts to ipfs_datasets_py and ipfs_accelerate_py

## Milestone A: Canonical Runtime And Contract Freeze

### A1. Lock production runtime path to unified MCP server
- [x] Declare unified MCP server as authoritative runtime in docs and startup flow
- [x] Add startup guard that warns or fails when deprecated MCP servers are used in production mode
- [x] Ensure CI and runbooks reference the canonical server path only

Definition of done:
- Runtime path documented and enforced
- Deprecated paths blocked or clearly marked unsupported for production

### A2. Publish VFS contract specification
- [x] Create a spec for all vfs tools and core methods
- [x] Standardize response keys for success, error, code, operation_id, lineage fields
- [x] Define required behavior for mount, resolve, read, write, copy, move, mkdir, rmdir, sync_to_ipfs, sync_from_ipfs

Definition of done:
- Spec committed and referenced by tests
- No ambiguity in tool response shapes

## Milestone B: Durable And Real Sync Semantics

### B1. Make sync state durable across process restart
- [x] Persist sync snapshots and sync state map to disk
- [x] Load persisted sync state at startup
- [x] Add corruption-safe load behavior and atomic write policy

Definition of done:
- Restart-safe sync_from_ipfs works after prior sync_to_ipfs
- Corrupt state file recovers safely without crashing

### B2. Implement real transport path for ipfs backend sync
- [x] Replace deterministic hash-only ipfs backend sync path with daemon or gateway-backed storage flow
- [x] Add explicit configuration to choose transport strategy and fallback behavior
- [x] Preserve deterministic fallback mode for test environments

Definition of done:
- End-to-end sync_to_ipfs and sync_from_ipfs use real transport in production mode
- Fallback mode still passes existing deterministic tests

### B3. Add conflict handling policy for sync_from_ipfs
- [x] Add overwrite policy
- [x] Add skip policy
- [x] Add strict policy
- [x] Emit policy choice in integration metadata

Definition of done:
- Policy-specific behavior verified by tests
- Response payload includes policy and conflict stats

## Milestone C: Metadata Index Lineage And Compatibility

### C1. Standardize ipfs_kit_py to ipfs_datasets_py operation envelope
- [x] Require operation_id, operation, path, backend, mount_point, timestamp
- [x] Include cid, source_cid, source_operation_id when available
- [x] Add schema_version field for metadata index entries

Definition of done:
- All mutation paths emit consistent envelope fields
- Metadata index entries include schema version and lineage keys

### C2. Harden remove and tombstone behavior
- [x] Keep removed_entry lineage in remove responses
- [x] Add optional tombstone mode for delete and unmount events
- [x] Ensure remove behavior is deterministic under concurrent writers

Definition of done:
- Removal contract tests pass for direct remove and record_ipfs_operation remove flow

### C3. Validate migration compatibility
- [x] Add compatibility reader for older index entries without lineage fields
- [x] Add migration tests for mixed old and new entry shapes

Definition of done:
- Legacy index files remain readable
- Listing and removal work across mixed schema versions

## Milestone D: Accelerate Pipeline Throughput For Index Builds

### D1. Extend accelerate caching policy
- [x] Add bounded cache policy validation for embeddings and model discovery
- [x] Add cache invalidation trigger controls
- [x] Expose cache metrics in metadata_index_snapshot

Definition of done:
- Cache hit rate visible and stable
- Cache size remains bounded under stress tests

### D2. Add batch enrichment path
- [x] Detect and use batch embedding capability when available
- [x] Fallback to per-item create_embedding if batch not available
- [x] Record per-batch timing metrics

Definition of done:
- Batch-capable path used when present
- Per-item fallback remains correct

### D3. Add queued enrichment with backpressure
- [x] Introduce queue for asynchronous enrichment jobs
- [x] Add retry budget and timeout budget controls
- [x] Add circuit-breaker behavior after repeated failures

Definition of done:
- Index refresh remains responsive under load
- Failure mode remains bounded and observable

## Milestone E: MCP Surface Cleanup

### E1. Eliminate advertised-but-not-implemented tools in unified server
- [x] Remove non-executable tools from tools list or implement handlers
- [x] Ensure tools list always matches callable behavior
- [x] Remove generic not_implemented responses for listed tools

Definition of done:
- tools/list and tools/call are contract-consistent

### E2. Resolve legacy server drift risk
- [x] Disable legacy servers by default
- [x] Keep adapter conformance tests only for supported compatibility paths
- [x] Mark legacy paths with clear retirement timeline

Definition of done:
- No accidental production path through deprecated servers

## Milestone F: Cross Platform Durability And Locking

### F1. Add non-posix locking fallback
- [x] Provide cross-platform lock strategy when fcntl is unavailable
- [x] Ensure lock behavior remains process-safe where possible
- [x] Add platform-conditional tests

Definition of done:
- Locking behavior documented and tested across supported environments

## Milestone G: CI Gates And Release Readiness

### G1. Add dedicated CI lane for VFS and integration contracts
- [x] Include VFS hardening suite
- [x] Include datasets metadata index contract suite
- [x] Include MCP VFS adapter contract suite
- [x] Include restart-safe sync and accelerate throughput tests

Definition of done:
- CI blocks release when core VFS integration contracts fail

### G2. Add release checklist for submodule scope hygiene
- [x] Validate no unrelated dirty files before release
- [x] Validate only intended submodule paths changed
- [x] Validate test matrix pass snapshot attached to release note

Definition of done:
- Release artifacts include scope and validation evidence

## Recommended Execution Order

1. Milestone A
2. Milestone B
3. Milestone C
4. Milestone D
5. Milestone E
6. Milestone F
7. Milestone G

## Verification Matrix To Run After Each Milestone

- pytest external/ipfs_kit/tests/test_vfs_contract_hardening.py -q
- pytest external/ipfs_kit/tests/test_datasets_metadata_index_contract.py -q
- pytest external/ipfs_kit/tests/test_mcp_vfs_adapter_contract.py -q
- pytest external/ipfs_kit/tests/test_vfs_jsonrpc.py external/ipfs_kit/tests/test_vfs_mcp_tools.py external/ipfs_kit/tests/test_vfs_mcp_integration.py -q

## Tracking Notes

- Keep this board as the single source of truth for VFS integration rollout.
- Mark each task with assignee and target date as implementation starts.
- Add links to PRs and test output under each completed task.
