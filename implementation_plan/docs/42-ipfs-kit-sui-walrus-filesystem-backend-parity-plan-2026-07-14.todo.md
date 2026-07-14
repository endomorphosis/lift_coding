# IPFS Kit Sui Walrus Filesystem Backend Parity Plan

Status: Active
Date: 2026-07-14
Canonical scope: `external/ipfs_kit`
Task prefix: `WALRUS-`
Owner: `ipfs_kit_py`

## Outcome

Make Sui Walrus a first-class optional `ipfs_kit_py` storage backend with the
same operational completeness as Iroh: `fsspec` URLs, VFS and bucket storage,
secure binary lifecycle, managed local service support, durable DuckDB
metadata, operator APIs, tests, packaging, and release evidence.

Walrus is not Iroh and parity does not mean copying its wire model. Walrus
objects remain epoch-bound blobs accessed through publishers and aggregators;
logical filesystem paths are implemented by a versioned metadata manifest.
The adapter must never imply that Walrus itself provides POSIX directories,
global listing, atomic rename, or permanent availability beyond the selected
storage and epoch policy.

## Audit Baseline

- Historical commits `a74c8e86` through `ed9ab23d` implemented a storage
  client, JSON path index, `WalrusFileSystem`, protocol registration, limited
  VFS creation, mocked tests, and documentation.
- Those files are absent from the active tree after later reconciliation even
  though the commits remain ancestors of the current submodule HEAD.
- The historical implementation used a JSON index. Production structured
  metadata must use DuckDB, consistent with the Iroh backend policy; SQLite is
  not an approved dependency or persistence format.
- The original seven tasks omitted binary supply-chain controls, managed
  service lifecycle, typed runtime boundaries, named backends, bucket tiering,
  security, observability, recovery, packaging gates, and release readiness.
- Restore prior work selectively and reconcile it with current Iroh/VFS code;
  do not reset the submodule or replace newer files wholesale.

## Architecture Rules

1. `WalrusFileSystem` is a dedicated `fsspec.AbstractFileSystem` registered as
   `walrus`, with explicit direct-blob and logical-namespace URL forms.
2. Publisher/aggregator HTTP APIs are the normal data path. The Walrus CLI is
   an optional bootstrap, diagnostics, and local-service tool behind a typed
   adapter, never invoked during package import.
3. Logical paths, reference counts, storage epochs, reconciliation, quotas,
   and migration journals are transactional DuckDB tables with schema/version
   migrations and single-writer coordination.
4. Missing credentials, unsupported versions, corrupt responses, expired
   epochs, or unhealthy services fail closed and never silently fall back to
   IPFS, Iroh, or local storage.
5. Secrets stay out of config files, URLs, logs, metrics, receipts, DuckDB
   rows, and process arguments; configs store credential references.
6. All network and live-chain tests are opt-in. The default suite uses golden
   fixtures and mocked transports and is deterministic offline.

## Phase 0 - Recovery, Compatibility, And Contracts

## WALRUS-001 Recover and inventory the historical Walrus implementation
- Status: completed
- Depends on: none
- Work: Recover only Walrus-specific content from commits `a74c8e86` through
  `ed9ab23d`, adapt integrations to the current tree, and produce a parity
  inventory against Iroh. Preserve newer Iroh and VFS changes.
- Outputs: recovered modules/tests/docs and `docs/walrus/parity-audit.md`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_storage.py tests/test_walrus_fsspec.py

## WALRUS-002 Pin supported Walrus and Sui compatibility
- Status: completed
- Depends on: WALRUS-001
- Work: Record supported CLI/service versions, networks, API shapes, platforms,
  release assets, checksums, licenses, epoch constraints, and upgrade bounds.
- Outputs: `docs/walrus/compatibility.md`, versioned release manifest/schema
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_compatibility.py

## WALRUS-003 Freeze filesystem, manifest, and backend contracts
- Status: completed
- Depends on: WALRUS-002
- Work: Specify URL grammar, blob/object IDs, namespaces, paths, manifest
  revisions, epoch policy, errors, consistency, permissions, and unsupported
  POSIX behavior with JSON Schemas and fixtures.
- Outputs: `docs/walrus/filesystem-contract.md`, schemas and golden fixtures
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_filesystem_contract.py

## WALRUS-004 Publish the capability and Iroh-parity matrix
- Status: completed
- Depends on: WALRUS-003
- Work: Classify every fsspec, VFS, lifecycle, security, and operator operation
  as native, emulated, or unsupported, with stable failure behavior.
- Outputs: `docs/walrus/capability-matrix.md`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_capability_matrix.py

## Phase 1 - Binary, Runtime, And Service Lifecycle

## WALRUS-005 Implement secure Walrus binary install and verification
- Status: completed
- Depends on: WALRUS-002
- Work: Add supported platform detection, pinned asset selection, digest and
  signature verification where available, atomic user-local install, locking,
  executable checks, and import-time side-effect prohibition.
- Outputs: `ipfs_kit_py/install_walrus.py`, fixtures and install receipts
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_install_walrus.py

## WALRUS-006 Add install, inspect, update, rollback, and PATH-safe CLI
- Status: completed
- Depends on: WALRUS-005
- Work: Provide explicit check/dry-run/update/rollback commands, retained prior
  versions, prerelease opt-in, redacted receipts, and `bash -lc` discovery.
- Outputs: `ipfs_kit_py/walrus_install_cli.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_install_cli.py

## WALRUS-007 Create the typed publisher, aggregator, and CLI runtime boundary
- Status: completed
- Depends on: WALRUS-002, WALRUS-003
- Work: Normalize upload/status/read/delete responses, timeouts, retries,
  cancellation, version skew, endpoint capability detection, and redaction.
- Outputs: `ipfs_kit_py/walrus/client.py`, `protocol.py`, `errors.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_runtime_client.py

## WALRUS-008 Implement service configuration and secure state layout
- Status: completed
- Depends on: WALRUS-003, WALRUS-007
- Work: Define client-only and managed publisher/aggregator modes, network,
  data/cache directories, ports, credential references, permissions, and
  environment/config precedence without inline secrets.
- Outputs: config schema, examples, `ipfs_kit_py/walrus/config.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_config.py

## WALRUS-009 Manage local Walrus services with real health verification
- Status: completed
- Depends on: WALRUS-005, WALRUS-008
- Work: Implement start/stop/restart/status, PID ownership, stale-PID repair,
  readiness probes, port-conflict detection, graceful shutdown, logs, and
  crash recovery. Recorded status alone is never health proof.
- Outputs: `ipfs_kit_py/walrus/service.py`, lifecycle documentation
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_service.py

## Phase 2 - DuckDB Metadata And fsspec

## WALRUS-010 Replace the historical JSON index with transactional DuckDB
- Status: completed
- Depends on: WALRUS-003, WALRUS-007
- Work: Store logical paths, manifests, blob/object IDs, epochs, costs,
  references, tombstones, quotas, and journals in DuckDB with migrations,
  transactions, locking, backup/export, and JSON-index migration.
- Outputs: `ipfs_kit_py/walrus/metadata.py`, migration tooling
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_metadata.py

## WALRUS-011 Implement read-side fsspec semantics
- Status: todo
- Depends on: WALRUS-007, WALRUS-010
- Work: Implement `info`, `exists`, `ls`, `find`, `glob`, `cat_file`, ranged
  reads, direct blob reads, cache validation, streaming, and sync/async paths.
- Outputs: `ipfs_kit_py/walrus_fsspec.py`
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_fsspec_reads.py tests/test_walrus_fsspec_async.py

## WALRUS-012 Implement safe write and mutation semantics
- Status: todo
- Depends on: WALRUS-010, WALRUS-011
- Work: Add staged writes, `pipe_file`, upload, manifest CAS, mkdir markers,
  copy/move metadata transactions, tombstone/delete policy, abort cleanup,
  concurrent writer handling, and idempotency.
- Outputs: write-capable filesystem and mutation journal
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_fsspec_writes.py

## WALRUS-013 Register protocols and package extras without side effects
- Status: todo
- Depends on: WALRUS-011
- Work: Register installed and vendored fsspec paths, `walrus` and immutable
  blob URL forms, optional dependencies, lazy imports, and wheel/sdist metadata.
- Outputs: package entry points, extras, registry hooks
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_fsspec_registration.py

## Phase 3 - VFS, Buckets, And Operator Surfaces

## WALRUS-014 Add named backend registry and VFS mounting
- Status: todo
- Depends on: WALRUS-008, WALRUS-012, WALRUS-013
- Work: Add validated named Walrus backends and VFS mounts with explicit
  backend dispatch, capability reporting, no silent fallback, and lineage.
- Outputs: backend registry/manager and VFS integration
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_vfs_integration.py

## WALRUS-015 Add Walrus as a bucket storage and tiering target
- Status: todo
- Depends on: WALRUS-014
- Work: Support create/mount/import/export/sync/reconcile, epoch-aware renewal,
  placement policies, IPFS/Iroh/local migrations, receipts, and rollback.
- Outputs: bucket adapter, tier policies, reconciliation receipts
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_bucket_tiering.py

## WALRUS-016 Add CLI, Python API, MCP, and diagnostics parity
- Status: todo
- Depends on: WALRUS-009, WALRUS-014
- Work: Expose filesystem, backend, service, health, install, migration, and
  diagnostics operations with stable JSON, redaction, and noninteractive use.
- Outputs: CLI/API/MCP tools and schemas
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_cli.py tests/test_walrus_mcp_api.py

## Phase 4 - Production Hardening

## WALRUS-017 Implement credentials, authorization, and threat controls
- Status: todo
- Depends on: WALRUS-008, WALRUS-012, WALRUS-016
- Work: Add credential-provider integration, rotation, endpoint allowlists,
  TLS requirements, SSRF defenses, path validation, response limits, secret
  scanning, least privilege, and actionable typed failures.
- Outputs: security module, threat model, golden attack vectors
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_security.py

## WALRUS-018 Add observability, quotas, performance, and cost controls
- Status: todo
- Depends on: WALRUS-009, WALRUS-015, WALRUS-017
- Work: Add redacted structured logs/metrics/traces, health diagnostics,
  latency/throughput baselines, cache limits, per-epoch cost/expiry alarms,
  quotas, backpressure, and retry budgets.
- Outputs: observability and performance modules/docs/baselines
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_observability.py tests/test_walrus_performance.py

## WALRUS-019 Add recovery, reconciliation, and multinode interoperability
- Status: todo
- Depends on: WALRUS-010, WALRUS-015, WALRUS-017
- Work: Cover interrupted uploads, stale manifests, missing/expired blobs,
  DuckDB backup/restore, publisher failover, index rebuild, node exchange, and
  deterministic migration receipts across Walrus, Iroh, and IPFS.
- Outputs: recovery tooling/docs and interoperability evidence
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_recovery.py tests/test_walrus_multinode.py

## WALRUS-020 Add CI, packaging, distribution, and live opt-in gates
- Status: todo
- Depends on: WALRUS-006, WALRUS-013, WALRUS-017, WALRUS-019
- Work: Test supported Python/platform matrices, wheel/sdist contents, optional
  dependency isolation, offline fixtures, install smoke, and opt-in testnet
  upload/read/delete without exposing credentials or spending unexpectedly.
- Outputs: CI scripts, packaging audit, testnet gate documentation
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_packaging.py

## WALRUS-021 Produce release readiness evidence and close the parity audit
- Status: todo
- Depends on: WALRUS-004, WALRUS-016, WALRUS-018, WALRUS-019, WALRUS-020
- Work: Run the complete Walrus suite, verify every Iroh-equivalent category is
  implemented or explicitly inapplicable with rationale, publish rollback,
  compatibility, SLO, migration, operations, and release evidence, and fail
  readiness on unresolved P0/P1 gaps.
- Outputs: `docs/walrus/release-readiness.md`, machine-readable readiness report
- Validation: cd external/ipfs_kit && python -m pytest -q tests/test_walrus_*.py

## Completion Gate

All 21 tasks must be completed, the focused Walrus suite must pass offline,
the optional live gate must be explicitly controlled and cost-bounded, the
submodule commit must be pinned by the parent repository, and the parity audit
must contain no unexplained Iroh-equivalent gaps.
