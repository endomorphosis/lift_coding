# IPFS Kit Iroh Filesystem Backend Improvement Plan

Status: Proposed
Date: 2026-07-12
Canonical scope: `external/ipfs_kit`
Task prefix: `IROH-`
Owner: `ipfs_kit_py`

## Outcome

Add Iroh as a first-class, optional storage backend for `ipfs_kit_py`: an
`fsspec` filesystem with `iroh://` URLs, a managed local Iroh service, verified
binary install/update/rollback, and selectable Iroh storage for the package's
virtual filesystems and buckets.

The result must support local persistence and peer transfer without pretending
that Iroh blobs are a POSIX filesystem. The adapter will maintain a versioned
directory manifest: paths and metadata live in the manifest, while file bytes
are immutable, BLAKE3-addressed Iroh blobs. Mutations publish a new manifest
revision atomically. Native Iroh hashes remain distinct from IPFS CIDs.

## Current Baseline And Constraints

- No Iroh implementation or configuration exists in `external/ipfs_kit`.
- `ipfs_kit_py/ipfs_fsspec.py` is the mature VFS integration path;
  `enhanced_fsspec.py` currently dispatches IPFS, Filecoin, Storacha, and
  Synapse with backend-specific branches.
- `backend_manager.py` persists named YAML backends but does not validate their
  schemas or secrets. `service_registry.py` has a richer async lifecycle but no
  Iroh service. `service_manager.py` only changes recorded status and must not
  be used as proof that a process is healthy.
- Binary installation is currently split across per-product installers and an
  opt-in setup hook. Iroh must use the same user-local binary directory while
  avoiding network or executable side effects during ordinary package import.
- Upstream Iroh is now a protocol library ecosystem: `iroh-blobs` supplies
  BLAKE3 content transfer and `iroh-docs` supplies an eventually consistent
  key/value layer. Exact CLI/binary/RPC availability is version-dependent, so
  the implementation must pin an audited release and place CLI interactions
  behind a versioned adapter.
- Browser clients cannot directly speak Iroh's custom QUIC/ALPN transport. Any
  SwissKnife/browser use requires an HTTP/WebTransport bridge and is not a
  hidden responsibility of the Python filesystem adapter.

## Architecture Decisions To Freeze

1. `IrohFileSystem` is a dedicated `AbstractFileSystem`, not another growing
   conditional inside `IPFSFileSystem`.
2. `iroh://<namespace>/<path>` addresses a mutable manifest namespace;
   `iroh+blob://<hash>` addresses immutable content. A read-only ticket form is
   allowed only after its grammar and credential handling are specified.
3. The first production transport is a supervised local sidecar with a stable,
   machine-readable RPC contract. A subprocess CLI adapter is permitted for
   bootstrap and diagnostics, not as the only per-operation data path.
4. Writes stage locally, hash/ingest the blob, then compare-and-swap the
   manifest revision. Rename and copy update manifests; they do not rewrite
   immutable content. Delete creates a tombstone and releases references; GC is
   a separate policy-controlled operation.
5. The backend is optional and fail-closed. Absence, version mismatch, corrupt
   output, or an unhealthy service returns typed errors and never silently
   falls back to IPFS or local storage.
6. Secrets (node key, write capability, tickets) never enter backend YAML,
   logs, metrics, process arguments, or VFS lineage. Config stores secret
   references resolved through the existing credential facilities.

## Phase 0 - Discovery, Contracts, And Version Pin

## IROH-001 Capture an upstream compatibility decision record
- Status: completed
- Depends on: none
- Work: Select the supported Iroh release, crates/binaries, platforms,
  checksums/signature source, RPC/CLI commands, data formats, and licenses.
  Record known breaking-version boundaries and an upgrade procedure.
- Outputs: `external/ipfs_kit/docs/iroh/compatibility.md`, machine-readable
  `external/ipfs_kit/ipfs_kit_py/resources/iroh-releases.json`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_compatibility_record.py
  supported platforms.

## IROH-002 Freeze the filesystem and backend contract
- Status: completed
- Depends on: IROH-001
- Work: Specify URL grammar, namespace identifiers, hashes, tickets, manifest
  schema, path normalization, error codes, sync/async behavior, consistency,
  permissions, conflict policy, and unsupported POSIX features.
- Outputs: `external/ipfs_kit/docs/iroh/filesystem-contract.md`, manifest and
  backend-config JSON Schemas, golden fixtures
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_filesystem_contract.py
  invalid hashes, leaked inline secrets, and unsupported schema versions.

## IROH-003 Define capability and conformance matrices
- Status: completed
- Depends on: IROH-002
- Work: Map every required fsspec/VFS operation (`ls`, `info`, `open`, ranged
  read, write, `mkdir`, `rm`, `cp`, `mv`, `find`, `glob`, `exists`, sync) to
  native, emulated, or unsupported Iroh behavior.
- Outputs: `external/ipfs_kit/docs/iroh/capability-matrix.md`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_capability_matrix.py
  calls have stable typed failures.

## Phase 1 - Binary Supply Chain And Runtime Adapter

## IROH-004 Implement a secure Iroh binary installer
- Status: completed
- Depends on: IROH-001
- Work: Add platform/architecture detection, pinned downloads, digest and
  signature verification where upstream provides it, atomic extraction,
  executable permissions, and user-local installation under
  `IPFS_KIT_BIN_DIR`. Reject unsupported targets.
- Outputs: `ipfs_kit_py/install_iroh.py`, installer unit fixtures
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_install_iroh.py
  truncated download, unsupported architecture, and non-executable result fail.

## IROH-005 Add explicit install, inspect, update, and rollback commands
- Status: completed
- Depends on: IROH-004
- Work: Add CLI commands with `--version`, `--check`, `--dry-run`, explicit
  prerelease opt-in, update locking, retained previous version, and rollback.
  Ordinary import/install remains side-effect free; setup auto-install stays
  behind `IPFS_KIT_AUTO_INSTALL_BINARIES`.
- Outputs: CLI handlers, install receipt containing version/source/digest/time
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_install_cli.py
  refusal, rollback, PATH-independent invocation, and `bash -lc` discovery.

## IROH-006 Introduce a versioned runtime client boundary
- Status: completed
- Depends on: IROH-001, IROH-002
- Work: Define typed Python request/results and adapters for sidecar RPC and
  diagnostic CLI. Centralize timeout, cancellation, JSON parsing, capability
  detection, redaction, and upstream-version translation.
- Outputs: `ipfs_kit_py/iroh/client.py`, `protocol.py`, `errors.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_runtime_client.py
  output, timeouts, cancellation, version skew, and redaction.

## Phase 2 - Managed Iroh Service

## IROH-007 Implement Iroh service configuration and state layout
- Status: completed
- Depends on: IROH-002, IROH-006
- Work: Define data directory, endpoint bind, relay/discovery policy, RPC
  endpoint, node identity reference, resource limits, log/receipt paths, and
  ownership/permissions. Support isolated named instances.
- Outputs: `ipfs_kit_py/iroh/config.py`, example config and migration logic
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_config.py
  collide silently, inline secrets are rejected, and migrations are atomic.

## IROH-008 Implement real service lifecycle management
- Status: completed
- Depends on: IROH-005, IROH-007
- Work: Create an `IrohService` for the canonical async registry with
  start/stop/restart/status, PID ownership, stale-PID recovery, readiness probe,
  graceful timeout then escalation, crash receipt, and idempotent concurrency.
  Provide foreground and managed-child modes; document systemd/launchd hooks.
- Outputs: `ipfs_kit_py/iroh/service.py`, service registry registration
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_service.py
  start, orphan, wrong PID, port conflict, crash loop, restart, and shutdown.

## IROH-009 Add health, diagnostics, and observability
- Status: completed
- Depends on: IROH-008
- Work: Report readiness separately from liveness, node ID, version, uptime,
  relay/direct connectivity, storage usage, peers, transfer counts/bytes,
  failures, latency, manifest conflicts, and GC state with bounded labels.
- Outputs: structured health receipt, metrics, diagnostic CLI/MCP operation
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_observability.py
  and no key, ticket, path content, or peer-sensitive value leaks.

## Phase 3 - Native Iroh Storage And Manifest Layer

## IROH-010 Implement blob ingest, fetch, range, and export primitives
- Status: completed
- Depends on: IROH-006, IROH-008
- Work: Stream files without full memory buffering; support expected-hash
  verification, progress/cancellation, resumable transfer when upstream permits,
  atomic destination writes, deduplication, and provider/ticket import.
- Outputs: `ipfs_kit_py/iroh/blob_store.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_blob_store.py
  ingest, corrupt payload, disconnect/resume, disk-full, and cancellation.

## IROH-011 Implement the versioned directory manifest store
- Status: completed
- Depends on: IROH-002, IROH-010
- Work: Store normalized entries (path, kind, blob hash, size, mode subset,
  mtime, metadata, revision, parent revision, tombstone) and publish with
  optimistic compare-and-swap. Use `iroh-docs` only if IROH-001 confirms a
  supported durable API; otherwise store signed manifest blobs plus a local
  atomic namespace-head database.
- Outputs: `ipfs_kit_py/iroh/manifest.py`, migration and recovery tools
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_manifest.py
  writers, conflict detection, tombstones, corrupt heads, and old-schema read.

## IROH-012 Add reference tracking and safe garbage collection
- Status: completed
- Depends on: IROH-011
- Work: Track references across namespaces/revisions; expose mark/sweep dry-run,
  retention windows, leases for active readers/writers, quotas, and repair.
- Outputs: `ipfs_kit_py/iroh/gc.py`, auditable GC receipt
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_gc.py
  during GC is recoverable; default policy never destroys newly unreferenced data.

## Phase 4 - Fsspec Implementation

## IROH-013 Build and register `IrohFileSystem`
- Status: completed
- Depends on: IROH-003, IROH-010, IROH-011
- Work: Implement a dedicated fsspec filesystem and buffered file classes for
  `iroh` and immutable `iroh+blob` protocols. Register through package entry
  points and the vendored-fsspec compatibility registry without import-time
  service startup.
- Outputs: `ipfs_kit_py/iroh_fsspec.py`, packaging entry points
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_fsspec_registration.py
  isolation, external fsspec, and vendored fallback all pass.

## IROH-014 Complete read/list/discovery semantics
- Status: pending
- Depends on: IROH-013
- Work: Implement `ls/detail`, `info`, `exists`, `isfile`, `isdir`, `find`,
  `walk`, `glob`, `cat`, `cat_file` ranges, `get_file`, and streaming `_open`.
- Outputs: read-side conformance suite
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_fsspec_reads.py
  trees, missing paths, immutable blob URLs, cold peer fetch, and offline cache.

## IROH-015 Complete mutation and transaction semantics
- Status: pending
- Depends on: IROH-013
- Work: Implement staged `_open` writes, `pipe_file`, `put_file`, mkdir, rm,
  copy, move, overwrite/exclusive modes, recursive behavior, and transaction
  batching. Publish bytes before manifest CAS and clean abandoned staging safely.
- Outputs: write-side conformance suite
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_fsspec_writes.py
  rename/copy dedupe, recursive deletion, retries, and restart recovery.

## IROH-016 Add async and performance behavior
- Status: pending
- Depends on: IROH-014, IROH-015
- Work: Provide fsspec async methods backed by AnyIO-compatible boundaries,
  bounded concurrency, connection reuse, read-ahead/range cache, multipart-like
  batching where supported, and backpressure.
- Outputs: async adapter and benchmark baseline
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_fsspec_async.py tests/test_iroh_performance.py
  bounds, memory bounds, parallel transfer, and latency/throughput budgets.

## Phase 5 - VFS, Buckets, Backend Manager, And Sync

## IROH-017 Make Iroh a validated named storage backend
- Status: pending
- Depends on: IROH-007, IROH-013
- Work: Extend backend configuration/manager APIs with type registry and schema
  validation for Iroh. Persist endpoint/namespace/policies and credential refs;
  return capability/health information and reject unknown settings.
- Outputs: backend plugin/registry integration, examples, migrations
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_backend_manager.py
  secret redaction, invalid configs, and legacy config compatibility.

## IROH-018 Mount Iroh in the canonical virtual filesystem
- Status: pending
- Depends on: IROH-014, IROH-015, IROH-017
- Work: Route `backend=iroh` and `iroh://` mounts through the canonical VFS,
  preserving operation envelopes, lineage, mount isolation, path policies,
  cache invalidation, and restart-safe mount state.
- Outputs: VFS factory/mount registry changes, Iroh integration adapter
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_vfs_integration.py
  pass; cross-backend copy IPFS/local/Iroh preserves bytes and lineage.

## IROH-019 Enable Iroh for virtual buckets and tiered storage
- Status: pending
- Depends on: IROH-018
- Work: Permit Iroh backend bindings in bucket creation, replication targets,
  tier policies, placement selection, capacity reporting, and reconciliation.
  Define whether a binding is primary, replica, cache, or archive.
- Outputs: bucket/tier policy schemas and reconciliation receipts
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_bucket_tiering.py
  quota rejection, duplicate content, and policy migration.

## IROH-020 Add explicit IPFS/Iroh synchronization
- Status: pending
- Depends on: IROH-018
- Work: Implement local/IPFS/Iroh import/export and sync with hash-domain
  separation (`cid` versus `iroh_hash`), durable checkpoints, conflict policies,
  resumability, lineage, and optional CAR staging. Never label an Iroh hash CID.
- Outputs: sync adapter, mapping/checkpoint schema, reconciliation receipt
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_ipfs_sync.py
  deleted entries, partial failure, hash verification, and idempotent replay.

## Phase 6 - User Surfaces And Operations

## IROH-021 Expose safe CLI operations
- Status: pending
- Depends on: IROH-009, IROH-017, IROH-020
- Work: Add binary, service, backend, namespace, blob, ticket, mount, sync, and
  GC commands with JSON output, confirmation for destructive work, dry-run,
  stable exit codes, and redaction.
- Outputs: CLI commands and operator runbook
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_cli.py
  confirmations, and shell/path portability.

## IROH-022 Expose governed MCP and API operations
- Status: pending
- Depends on: IROH-021
- Work: Add only implemented Iroh capabilities to the unified MCP server and
  storage API. Separate read/control/destructive permissions; validate inputs;
  emit operation IDs, progress, audit records, and typed errors.
- Outputs: MCP tool schemas/handlers and OpenAPI updates
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_mcp_api.py
  redaction, malformed tickets, and destructive confirmation tests pass.

## IROH-023 Document deployment and recovery
- Status: pending
- Depends on: IROH-009, IROH-020
- Work: Document install/upgrade/rollback, ports/firewall/relay, backups of node
  identity and manifests, namespace sharing, outage modes, disaster recovery,
  key rotation, data export, GC, and complete uninstall without data loss.
- Outputs: `external/ipfs_kit/docs/iroh/{operations,security,recovery}.md`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_operations_docs.py

## Phase 7 - Security, Interoperability, CI, And Release

## IROH-024 Complete threat model and hardening
- Status: pending
- Depends on: IROH-002, IROH-008, IROH-011, IROH-022
- Work: Threat-model malicious tickets/peers/manifests, path traversal, symlinks,
  decompression/archive attacks, key theft, replay, rollback, resource
  exhaustion, RPC exposure, relay metadata, and supply-chain compromise.
- Outputs: threat model, security test vectors, credential rotation procedure
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_security.py
  permissions, log scan, resource limits, and dependency/license audit pass.

## IROH-025 Run real multi-node interoperability tests
- Status: pending
- Depends on: IROH-016, IROH-020, IROH-024
- Work: Test two or more isolated nodes over direct LAN, relay fallback, NAT-like
  container topology, interruption, version skew, key rotation, and large data.
  Keep offline unit tests separate from opt-in network tests.
- Outputs: deterministic harness and interoperability evidence JSON
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_multinode.py
  and bounded-resource assertions pass on Linux and macOS targets.

## IROH-026 Add CI and packaging gates
- Status: pending
- Depends on: IROH-005, IROH-013, IROH-025
- Work: Add unit, fsspec conformance, async, service, installer, security,
  packaging, and opt-in multi-node lanes. Test Python 3.12/3.13, supported OS and
  architectures, with and without external fsspec, and without Iroh installed.
- Outputs: CI workflows, wheel/sdist smoke tests, coverage report
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_packaging.py
  remains usable without Iroh; extras and binaries are reproducible.

## IROH-027 Stage rollout and release sign-off
- Status: pending
- Depends on: IROH-023, IROH-024, IROH-026
- Work: Release behind `iroh.enabled=false`, then experimental opt-in, canary,
  and supported status. Define rollback, SLOs, compatibility window, migration,
  deprecation, data portability, and support ownership.
- Outputs: readiness report, test/benchmark/security receipts, release notes
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_iroh_release_readiness.py
  rollback preserve manifests/data; no critical/high unresolved findings.

## Dependency-Critical Execution Order

1. IROH-001 through IROH-003: freeze reality and contracts.
2. IROH-004 through IROH-009: make install and service management trustworthy.
3. IROH-010 through IROH-012: establish durable native storage semantics.
4. IROH-013 through IROH-016: deliver fsspec behavior and performance.
5. IROH-017 through IROH-020: connect named backends, VFS, buckets, and sync.
6. IROH-021 through IROH-023: expose operator and API surfaces.
7. IROH-024 through IROH-027: harden, interoperate, package, and release.

Parallel work is safe only after its shared contract dependency is complete.
In particular, installer/service work may run beside manifest prototyping after
IROH-002, while VFS integration must wait for the fsspec contract suite.

## Release Gates

- Contract: all schemas and fsspec advertised-capability tests pass.
- Integrity: every read verifies the expected Iroh hash; namespace changes are
  revisioned and atomic; IPFS CIDs and Iroh hashes remain distinguishable.
- Durability: service, manifest, mount, upload, and sync recovery pass after
  forced termination at each write boundary.
- Security: verified binaries, private keys, least-privilege local RPC, bounded
  untrusted inputs, redacted receipts, and no unresolved critical/high issues.
- Operations: installer rollback, service status, backup/restore, key rotation,
  GC dry-run, data export, and clean uninstall are rehearsed.
- Compatibility: supported Python/OS/architecture matrix passes; base
  `ipfs_kit_py` still imports and operates when Iroh is absent.
- Performance: streaming memory is bounded; no whole-file buffering; benchmark
  budgets and regression thresholds are recorded before supported release.

## Required Evidence Per Completed Task

Each task completion must add: changed paths, exact validation command, exit
status, test counts, artifact paths, upstream/version assumptions, remaining
risks, and rollback notes. Live service tasks must also record PID, executable
path, version, RPC identity, readiness, and state directory. Network tests must
record topology without recording secrets or reusable tickets.

## Initial Supervisor Command

After the supervisor parser accepts the board format, initialize state without
implementation and keep execution in this checkout:

```bash
python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
  --once \
  --todo-path implementation_plan/docs/40-ipfs-kit-iroh-filesystem-backend-plan-2026-07-12.todo.md \
  --state-dir tmp/ipfs_kit_iroh_supervisor/state \
  --task-prefix '## IROH-' \
  --state-prefix ipfs_kit_iroh \
  --no-implement \
  --no-ephemeral-worktree
```

Do not start an implementation daemon until IROH-001 has pinned a concrete
upstream release and the supervisor preflight recognizes all dependencies.

## Upstream References Consulted

- Iroh project: https://github.com/n0-computer/iroh
- The upstream project describes `iroh-blobs` as BLAKE3 content-addressed blob
  transfer and `iroh-docs` as an eventually consistent key/value store.
- Browser transport limitation reference:
  https://github.com/n0-computer/iroh-live/blob/main/docs/guide/browser-relay.md
