# Proof-Carrying Context Engine v0.1 supervisor task board

Machine-readable Markdown for ipfs_accelerate_py.agent_supervisor. Task headings use the canonical PCCE- prefix. The board namespace and parent objective identity are proof-carrying-context-engine-v0.1 and PCCE-G000.

Parent objective: create, implement, test, and qualify an installable Proof-Carrying Context Engine v0.1 that exposes the existing semantic-compression, model-routing, incremental-verification, assurance, and proof-sealing implementations through one provider-neutral runtime and CLI. It augments existing coding agents; it does not create another coding agent or duplicate completed subsystems.

Goal tree:

- PCCE-G000 — Proof-Carrying Context Engine v0.1 parent objective.
- PCCE-G100 — Epic A: implementation inventory and contract freeze.
- PCCE-G200 — Epic B: stable runtime facade and governed lifecycle.
- PCCE-G300 — Epic C: agent and external-patch adapters.
- PCCE-G400 — Epic D: one-command CLI and stable reports.
- PCCE-G500 — Epic E: installability, reproducible packaging, and example.
- PCCE-G600 — Epic F: frozen external generalization benchmark.
- PCCE-G700 — Epic G: security and trust-boundary hardening.
- PCCE-G800 — Epic H: CI, release qualification, and go/no-go.

## Execution wave graph

    W00  PCCE-000
      ↓
    W01  PCCE-001 | PCCE-002 | PCCE-003 | PCCE-004
      ↓
    W02  PCCE-005
      ↓
    W03  PCCE-006
      ↓
    W04  PCCE-007
      ↓
    W05  PCCE-008 | PCCE-009 | PCCE-010
      ↓
    W06  PCCE-011
      ↓
    W07  PCCE-020 | PCCE-022 | PCCE-023
      ↓
    W08  PCCE-021
      ↓
    W09  PCCE-024
      ↓
    W10  PCCE-025
      ↓
    W11  PCCE-030 | PCCE-040 | PCCE-043
      ↓
    W12  PCCE-031 | PCCE-032 | PCCE-033 | PCCE-034 | PCCE-042
      ↓
    W13  PCCE-035
      ↓
    W14  PCCE-041
      ↓
    W15  PCCE-044
      ↓
    W16  PCCE-050 | PCCE-051 | PCCE-052 | PCCE-055
      ↓
    W17  PCCE-053
      ↓
    W18  PCCE-054
      ↓
    W19  PCCE-056
      ↓
    W20  PCCE-060 | PCCE-070
      ↓
    W21  PCCE-061 | PCCE-062 | PCCE-063 | PCCE-064 | PCCE-065 | PCCE-066 | PCCE-071 | PCCE-072 | PCCE-073 | PCCE-074
      ↓
    W22  PCCE-067 | PCCE-075
      ↓
    W23  PCCE-068 | PCCE-076
      ↓
    W24  PCCE-080
      ↓
    W25  PCCE-081
      ↓
    W26  PCCE-082
      ↓
    W27  PCCE-083

## Board defaults and launch invariants

- Every path is exact and root-relative to the proof-carrying-context-engine control checkout. Repository roots are external/ipfs_datasets, external/ipfs_kit, external/ipfs_accelerate, and Mcp-Plus-Plus; generated evidence is under artifacts/proof_carrying_context_engine.
- The supervisor must bind the parent objective, task ID, board revision, repository remote, exact commit, exact tree, submodule/gitlink identities, owned paths, lease, mutation permit, fence, idempotency key, and isolated worktree before dispatch. Assigned-worktree names below are reservations, not authority until that binding receipt exists.
- Before mutation, each worker records clean status and runs the declared pre-change tests. It may mutate only its Owned paths plus its unique task receipt. It runs focused and affected integration tests, records partial effects, and publishes a content-addressed task receipt before merge.
- Concurrent launch is allowed only inside a displayed wave after all dependencies are sealed. Owned paths in a concurrent wave do not overlap. Cross-wave parallelism requires an explicit merge plan and conflict-graph proof.
- Production and supervised evidence fails closed on stale, invalid, unavailable, unsigned-when-required, simulated, or pseudo-CID inputs. Simulation and replay remain visibly labeled and cannot be promoted into live production evidence.
- Retry loops are bounded to two repair attempts after the first attempt. A repeated failure must preserve all failed-attempt receipts and then minimize the counterexample, expand context, escalate route, request human review, or record an external blocker/no-go.
- Protected control inputs are docs/architecture/proof_carrying_context_engine_v0_1.todo.md, docs/architecture/proof_carrying_context_engine_v0_1.objectives.md, external/ipfs_accelerate/config/agent_supervisor_proof_carrying_context_engine_scheduler.json, and external/ipfs_accelerate/scripts/ops/agent_supervisor/proof_carrying_context_engine_supervisor.py. No schedulable implementation task owns or may edit them; only the fenced supervisor/operator may project status and final artifact identities.
- Default completion is automatic only after all Acceptance criteria, Required tests, Required evidence, clean-worktree postcheck, and receipt-CID verification pass. A no-go artifact is a valid result only where a task explicitly permits it; it is never evidence that the unavailable capability passed.
- Rollback never rewrites shared history. Discard an unmerged isolated worktree; if a task commit was merged, revert only that task commit, invalidate dependent receipts, restore the previous CAS root where applicable, and record repair_required or partial_effect.

## PCCE-000 Bootstrap and freeze the coordinated board

- Status: completed
- Completion: manual
- Is schedulable: false
- Review only: true
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/receipts/PCCE-000.json
- Objective: Establish PCCE-G000, the eight epic goals, stable task identities, non-overlapping ownership, dependency waves, and fail-closed launch defaults without granting implementation workers control-plane authority.
- Depends on:
- Priority: P0
- Risk classification: control-critical
- Execution mode: operator-only board bootstrap
- Allowed effects: Record the reviewed board bootstrap receipt and immutable board content identity.
- Prohibited effects: Implement product code; mutate any external repository; let a worker edit protected plan, board, scheduler, or supervisor files.
- Acceptance criteria: The board contains exactly PCCE-000, PCCE-001 through PCCE-011, PCCE-020 through PCCE-025, PCCE-030 through PCCE-035, PCCE-040 through PCCE-044, PCCE-050 through PCCE-056, PCCE-060 through PCCE-068, PCCE-070 through PCCE-076, and PCCE-080 through PCCE-083; every block has every required field; dependencies are acyclic and follow the declared merge order.
- Required tests: Parse all PCCE headings; verify unique IDs, required fields, exact namespace, acyclic dependencies, non-overlapping concurrent Owned paths, and protected-path exclusion.
- Required evidence: Board byte digest; parser report; dependency graph; protected-path audit; operator approval identity.
- Rollback procedure: Supersede with a new explicitly versioned reviewed board; never silently rewrite an admitted board identity.
- Assigned worktree: proof-carrying-context-engine-control
- Final result CID or artifact identity: board Git blob and artifacts/proof_carrying_context_engine/receipts/PCCE-000.json; resolved by launch seal
- Goal id: PCCE-G000
- Outputs: artifacts/proof_carrying_context_engine/receipts/PCCE-000.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/api/agent_supervisor -k task_board
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/control/bootstrap
- Parallel lane: pcce-control
- Resource class: cpu-small
- Implementation timeout seconds: 900
- Predicted files: artifacts/proof_carrying_context_engine/receipts/PCCE-000.json
- Allowed paths: artifacts/proof_carrying_context_engine/receipts/PCCE-000.json
- Conflict policy: Operator-only bootstrap. Protected control documents are outside every schedulable task mutation permit.
- Acceptance: One parseable, complete, acyclic, namespace-stable board is admitted as the sole execution source for PCCE-G000.

## PCCE-001 Inventory datasets semantic and evaluation authorities

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json, artifacts/proof_carrying_context_engine/receipts/PCCE-001.json
- Objective: Inspect the bound datasets commit, tree, code, tests, schemas, package exports, documentation, and visible WIP refs to identify canonical implementations relevant to all eleven reported subsystems and datasets ownership claims.
- Depends on: PCCE-000
- Priority: P0
- Risk classification: medium-discovery
- Execution mode: supervised read-only inventory
- Allowed effects: Read external/ipfs_datasets and its in-repository Git refs; write only the inventory and task receipt.
- Prohibited effects: Trust README names without code and test evidence; mutate datasets; inspect sibling worktrees or hidden evaluator data; treat an unmerged WIP ref as canonical.
- Acceptance criteria: For every candidate or explicit absence, record subsystem name, repository, canonical module path, public API, schema, persistence and execution dependencies, tests, docs, maturity, duplicate or legacy implementations, missing integration points, exact commit/tree/blob evidence, and relevant WIP-ref differences.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json
- Required evidence: Clean commit/tree identity; package-export and AST inspection; focused test collection/execution results; documentation-to-code discrepancy log; ref names and inspected commit IDs.
- Rollback procedure: Discard the isolated inventory worktree and invalidate only this inventory/receipt; no source rollback is permitted because source mutation is prohibited.
- Assigned worktree: pcce-PCCE-001
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json, artifacts/proof_carrying_context_engine/receipts/PCCE-001.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/inventory-datasets
- Parallel lane: pcce-a-inventory-datasets
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Predicted files: artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json, artifacts/proof_carrying_context_engine/receipts/PCCE-001.json
- Allowed paths: artifacts/proof_carrying_context_engine/inventory/ipfs_datasets.json, artifacts/proof_carrying_context_engine/receipts/PCCE-001.json
- Conflict policy: Read-only against the exact bound datasets tree; only unique central artifacts may be written.
- Acceptance: Inventory claims are traceable to code plus current tests, and every name mismatch, duplicate, gap, or WIP-only implementation is explicit.

## PCCE-002 Inventory kit persistence and artifact authorities

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_kit_py
- Owned paths: artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json, artifacts/proof_carrying_context_engine/receipts/PCCE-002.json
- Objective: Inspect the bound kit commit, tree, code, tests, storage schemas, package exports, documentation, and visible WIP refs to locate immutable artifact, repository-state, receipt, proof-forest, CAS-root, WAL, local, and optional IPFS authorities.
- Depends on: PCCE-000
- Priority: P0
- Risk classification: high-integrity-discovery
- Execution mode: supervised read-only inventory
- Allowed effects: Read external/ipfs_kit and its in-repository Git refs; write only the inventory and task receipt.
- Prohibited effects: Infer durability from API names; mutate kit; contact an IPFS daemon; inspect sibling worktrees; treat pseudo-CIDs or WIP-only code as released authority.
- Acceptance criteria: The inventory provides every required subsystem field, exact API and persistence behavior, WAL/CAS/fencing evidence, real-CID behavior, local hermetic capability, optional-network boundary, current tests/docs/maturity, duplicates, WIP differences, and missing integration points.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json
- Required evidence: Clean commit/tree identity; AST/export inspection; storage and corruption-test results; CID vectors; visible-ref comparison ledger.
- Rollback procedure: Discard the isolated inventory worktree and invalidate only this inventory/receipt; source remains unchanged.
- Assigned worktree: pcce-PCCE-002
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json, artifacts/proof_carrying_context_engine/receipts/PCCE-002.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/inventory-kit
- Parallel lane: pcce-a-inventory-kit
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Predicted files: artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json, artifacts/proof_carrying_context_engine/receipts/PCCE-002.json
- Allowed paths: artifacts/proof_carrying_context_engine/inventory/ipfs_kit.json, artifacts/proof_carrying_context_engine/receipts/PCCE-002.json
- Conflict policy: Read-only against the exact bound kit tree; unique evidence files prevent inventory-lane collisions.
- Acceptance: Every persistence claim is backed by implementation and executable tests, with unavailable, legacy, provisional, and WIP-only paths separated.

## PCCE-003 Inventory accelerator orchestration authorities

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-003.json
- Objective: Inspect the bound accelerator commit, tree, supervisor/runtime code, tests, schemas, exports, docs, and visible WIP refs to locate routing, verification, worktree, cancellation, retry, assurance, proof-sealing, semantic-compression, and self-hosting authorities.
- Depends on: PCCE-000
- Priority: P0
- Risk classification: high-orchestration-discovery
- Execution mode: supervised read-only inventory
- Allowed effects: Read external/ipfs_accelerate and its in-repository Git refs; write only the inventory and receipt.
- Prohibited effects: Trust subsystem labels without call-path and test evidence; mutate runtime code or supervisor state; launch agents; inspect sibling worktrees or hidden benchmark answers.
- Acceptance criteria: For each reported subsystem candidate or absence, capture all required inventory fields, actual lifecycle position, production versus simulation behavior, concurrency/lease/fence semantics, current tests/docs/maturity, duplicate and legacy paths, WIP differences, and integration gaps.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json
- Required evidence: Clean commit/tree identity; AST and import graph; focused tests; production call-path trace; mock/simulation audit; visible-ref commit ledger.
- Rollback procedure: Discard the isolated inventory worktree and invalidate only this inventory/receipt; source remains unchanged.
- Assigned worktree: pcce-PCCE-003
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-003.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/inventory-accelerate
- Parallel lane: pcce-a-inventory-accelerate
- Resource class: cpu-medium
- Implementation timeout seconds: 5400
- Predicted files: artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-003.json
- Allowed paths: artifacts/proof_carrying_context_engine/inventory/ipfs_accelerate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-003.json
- Conflict policy: Read-only against the exact bound accelerator tree; no supervisor runtime or task state may be changed.
- Acceptance: The inventory distinguishes canonical live behavior from stubs, mocks, simulations, aliases, retired modules, and WIP-only candidates using code and test evidence.

## PCCE-004 Inventory MCP++ interoperability authorities

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/Mcp-Plus-Plus
- Owned paths: artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json, artifacts/proof_carrying_context_engine/receipts/PCCE-004.json
- Objective: Inspect the bound MCP++ commit, tree, schemas, vectors, validators, tests, docs, and visible WIP refs to identify reusable invocation and receipt contracts without granting MCP++ runtime authority.
- Depends on: PCCE-000
- Priority: P0
- Risk classification: high-contract-discovery
- Execution mode: supervised read-only inventory
- Allowed effects: Read Mcp-Plus-Plus and its in-repository Git refs; write only the inventory and receipt.
- Prohibited effects: Invent a new MCP++ profile; mutate schemas; infer canonicalization from examples alone; assign production orchestration, persistence, or model authority to MCP++.
- Acceptance criteria: Record all required inventory fields for compatible invocation, receipt, vector, canonicalization, CID, status, and error contracts; identify duplicates, version skew, test coverage, WIP differences, and every missing narrow v0.1 interop surface.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json
- Required evidence: Clean commit/tree identity; schema and validator inspection; canonical-vector test results; visible-ref commit ledger; runtime-authority exclusion audit.
- Rollback procedure: Discard the isolated inventory worktree and invalidate only this inventory/receipt; MCP++ source remains unchanged.
- Assigned worktree: pcce-PCCE-004
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json, artifacts/proof_carrying_context_engine/receipts/PCCE-004.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/inventory-mcplusplus
- Parallel lane: pcce-a-inventory-mcplusplus
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Predicted files: artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json, artifacts/proof_carrying_context_engine/receipts/PCCE-004.json
- Allowed paths: artifacts/proof_carrying_context_engine/inventory/mcp_plus_plus.json, artifacts/proof_carrying_context_engine/receipts/PCCE-004.json
- Conflict policy: Read-only against the exact bound MCP++ tree; unique inventory output is the only mutation.
- Acceptance: MCP++ reuse is evidence-backed, narrow, versioned, and explicitly free of production runtime authority.

## PCCE-005 Select canonical ownership and migration map

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json, artifacts/proof_carrying_context_engine/contracts/migration_map.json, artifacts/proof_carrying_context_engine/receipts/PCCE-005.json
- Objective: Reconcile the four inventories into one canonical implementation map, confirm the prescribed repository boundaries, and create a bounded migration item for every violation needed by the v0.1 runtime.
- Depends on: PCCE-001, PCCE-002, PCCE-003, PCCE-004
- Priority: P0
- Risk classification: architecture-critical
- Execution mode: supervised evidence synthesis
- Allowed effects: Read sealed inventory artifacts; write the ownership and migration manifests and receipt.
- Prohibited effects: Select by README wording, module name, or recency alone; move code; broaden migrations into legacy cleanup; assign MCP++ runtime authority.
- Acceptance criteria: All eleven reported subsystems map to canonical code/test evidence or an explicit unavailable result; datasets, kit, accelerator, and MCP++ boundaries match the stated ownership model; every violation has source, target, compatibility strategy, task ID, risk, and dependent invalidation set.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json; python -m json.tool artifacts/proof_carrying_context_engine/contracts/migration_map.json
- Required evidence: Four admitted inventory CIDs; deterministic reconciliation output; duplicate resolution rationale; ownership-boundary review.
- Rollback procedure: Invalidate the synthesis artifacts and all dependent contract receipts; do not mutate inventoried repositories.
- Assigned worktree: pcce-PCCE-005
- Final result CID or artifact identity: pending CIDs for canonical_ownership.json and migration_map.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json, artifacts/proof_carrying_context_engine/contracts/migration_map.json, artifacts/proof_carrying_context_engine/receipts/PCCE-005.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json && python -m json.tool artifacts/proof_carrying_context_engine/contracts/migration_map.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/ownership
- Parallel lane: pcce-a-ownership
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Predicted files: artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json, artifacts/proof_carrying_context_engine/contracts/migration_map.json, artifacts/proof_carrying_context_engine/receipts/PCCE-005.json
- Allowed paths: artifacts/proof_carrying_context_engine/contracts/canonical_ownership.json, artifacts/proof_carrying_context_engine/contracts/migration_map.json, artifacts/proof_carrying_context_engine/receipts/PCCE-005.json
- Conflict policy: Inventory CIDs are immutable inputs; any ambiguous owner fails closed and blocks contract freeze.
- Acceptance: One deterministic ownership/migration map names the actual canonical implementation for every integrated capability and limits migrations to v0.1 blockers.

## PCCE-006 Freeze v0.1 shared schemas and taxonomies

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/Mcp-Plus-Plus
- Owned paths: Mcp-Plus-Plus/schemas/proof-context/v0.1/repository-state.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/semantic-capsule.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/context-pack.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/invalidation-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/verification-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/model-route-decision.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/execution-receipt.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/proof-unit.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/incremental-seal.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/qualification-result.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/error-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/status-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/canonicalization.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/cid-behavior.schema.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py, artifacts/proof_carrying_context_engine/receipts/PCCE-006.json
- Objective: Freeze exact v0.1 narrow interoperability contracts derived from canonical implementations for repository state, capsules, ContextPacks, plans, routes, receipts, proof units, seals, qualification, taxonomies, canonicalization, and CID behavior.
- Depends on: PCCE-005
- Priority: P0
- Risk classification: contract-critical
- Execution mode: supervised schema implementation
- Allowed effects: Add the versioned MCP++ schemas, schema tests, and unique receipt.
- Prohibited effects: Create production runtime logic; silently rename canonical fields; accept unknown status/error values; define pseudo-CIDs; change a frozen schema without version and migration.
- Acceptance criteria: Schemas are closed, versioned 0.1, bounded, provider-neutral, consistent with actual APIs, and distinguish succeeded, rejected, verification_failed, proof_failed, assurance_failed, context_insufficient, model_escalation_required, human_review_required, unavailable, timeout, cancelled, invalid, stale, simulated, infrastructure_failure, partial_effect, and repair_required.
- Required tests: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py
- Required evidence: Ownership-map CID; schema digests; validator results; field-by-field implementation trace; explicit migration/versioning rule.
- Rollback procedure: Revert only the schema task commit before dependent publication; after publication, issue a new schema version and invalidate all dependent receipts instead of editing v0.1 in place.
- Assigned worktree: pcce-PCCE-006
- Final result CID or artifact identity: pending schema-set CID and artifacts/proof_carrying_context_engine/receipts/PCCE-006.json
- Goal id: PCCE-G100
- Outputs: Mcp-Plus-Plus/schemas/proof-context/v0.1/repository-state.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/semantic-capsule.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/context-pack.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/invalidation-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/verification-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/model-route-decision.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/execution-receipt.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/proof-unit.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/incremental-seal.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/qualification-result.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/error-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/status-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/canonicalization.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/cid-behavior.schema.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py, artifacts/proof_carrying_context_engine/receipts/PCCE-006.json
- Validation: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/schema-freeze
- Parallel lane: pcce-a-schema
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: Mcp-Plus-Plus/schemas/proof-context/v0.1/repository-state.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/semantic-capsule.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/context-pack.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/invalidation-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/verification-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/model-route-decision.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/execution-receipt.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/proof-unit.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/incremental-seal.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/qualification-result.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/error-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/status-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/canonicalization.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/cid-behavior.schema.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py, artifacts/proof_carrying_context_engine/receipts/PCCE-006.json
- Allowed paths: Mcp-Plus-Plus/schemas/proof-context/v0.1/repository-state.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/semantic-capsule.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/context-pack.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/invalidation-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/verification-plan.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/model-route-decision.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/execution-receipt.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/proof-unit.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/incremental-seal.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/qualification-result.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/error-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/status-taxonomy.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/canonicalization.schema.json, Mcp-Plus-Plus/schemas/proof-context/v0.1/cid-behavior.schema.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py, artifacts/proof_carrying_context_engine/receipts/PCCE-006.json
- Conflict policy: MCP++ owns only shared schemas and vectors. Canonical producer semantics stay with datasets, kit, or accelerator.
- Acceptance: All v0.1 wire contracts have exact versions and reject unknown, stale, simulated-as-live, malformed, and identity-inconsistent values.

## PCCE-007 Freeze canonical vectors and compatibility matrix

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/Mcp-Plus-Plus
- Owned paths: Mcp-Plus-Plus/conformance/vectors/proof-context-v0.1.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py, Mcp-Plus-Plus/docs/interop/proof-context-v0.1.md, artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json, artifacts/proof_carrying_context_engine/receipts/PCCE-007.json
- Objective: Freeze canonical JSON bytes, real CID behavior, positive and negative vectors, and an exact four-repository compatibility matrix for every v0.1 contract.
- Depends on: PCCE-006
- Priority: P0
- Risk classification: identity-critical
- Execution mode: supervised conformance implementation
- Allowed effects: Add canonical vectors, vector tests, interop documentation, compatibility matrix, and receipt.
- Prohibited effects: Copy a second canonicalizer into a production package; bless pseudo-CIDs; omit negative/stale/simulated vectors; edit schemas without a new version.
- Acceptance criteria: Equivalent values have identical canonical bytes and CIDv1 identities across consumers; unknown fields, NaN/Infinity, wrong parents, stale roots, malformed CIDs, and simulated promotion fail; the matrix pins commit/tree, schema support, migration, and producer/consumer direction for all four repositories.
- Required tests: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py; python -m json.tool artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json
- Required evidence: Schema-set CID; vector CID; cross-repository probe output; compatibility matrix CID; negative-vector results.
- Rollback procedure: Revert before dependent admission; after admission, publish replacement vectors under a new contract version and invalidate dependent tasks.
- Assigned worktree: pcce-PCCE-007
- Final result CID or artifact identity: pending vector-set and compatibility-matrix CIDs
- Goal id: PCCE-G100
- Outputs: Mcp-Plus-Plus/conformance/vectors/proof-context-v0.1.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py, Mcp-Plus-Plus/docs/interop/proof-context-v0.1.md, artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json, artifacts/proof_carrying_context_engine/receipts/PCCE-007.json
- Validation: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py && python -m json.tool artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/vectors-compatibility
- Parallel lane: pcce-a-vectors
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: Mcp-Plus-Plus/conformance/vectors/proof-context-v0.1.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py, Mcp-Plus-Plus/docs/interop/proof-context-v0.1.md, artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json, artifacts/proof_carrying_context_engine/receipts/PCCE-007.json
- Allowed paths: Mcp-Plus-Plus/conformance/vectors/proof-context-v0.1.json, Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py, Mcp-Plus-Plus/docs/interop/proof-context-v0.1.md, artifacts/proof_carrying_context_engine/contracts/compatibility_matrix.json, artifacts/proof_carrying_context_engine/receipts/PCCE-007.json
- Conflict policy: Vector bytes and schema versions are immutable inputs to all later tasks; any mismatch invalidates dependent work rather than being normalized away.
- Acceptance: Cross-repository contract and identity compatibility is executable, pinned, fail-closed, and migration-aware.

## PCCE-008 Remove datasets v0.1 integration blockers

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/contracts.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/provider.py, external/ipfs_datasets/tests/proof_context/test_v01_provider.py, artifacts/proof_carrying_context_engine/receipts/PCCE-008.json
- Objective: Add the smallest versioned datasets-owned port over the inventoried canonical semantic repository state, capsules, ContextPacks, invalidation, sufficiency, task/benchmark specs, and semantic outcome comparison needed by v0.1.
- Depends on: PCCE-007
- Priority: P0
- Risk classification: high-semantic-integrity
- Execution mode: supervised bounded migration
- Allowed effects: Add narrow adapters and focused tests in the declared paths; repair only migration-map blockers expressible there.
- Prohibited effects: Implement another analyzer, capsule compiler, or context optimizer; import sibling source paths; weaken freshness; manufacture missing facts; refactor unrelated legacy code.
- Acceptance criteria: The port lazily resolves canonical implementations, proves schema/API compatibility, preserves producer identities, requires exact scanned-tree source for opaque or insufficient content, fails stale/unavailable, and imports without I/O or specially placed siblings.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/test_v01_provider.py
- Required evidence: Pre-change canonical tests; adapter tests; compatibility-vector results; import trace; migration-map items closed or explicitly blocked.
- Rollback procedure: Revert only the adapter task commit, discard its worktree, and invalidate downstream receipts; canonical semantic state is untouched.
- Assigned worktree: pcce-PCCE-008
- Final result CID or artifact identity: pending task receipt and datasets adapter tree identity
- Goal id: PCCE-G100
- Outputs: external/ipfs_datasets/ipfs_datasets_py/proof_context/contracts.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/provider.py, external/ipfs_datasets/tests/proof_context/test_v01_provider.py, artifacts/proof_carrying_context_engine/receipts/PCCE-008.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/test_v01_provider.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/datasets-blockers
- Parallel lane: pcce-a-datasets
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/proof_context/contracts.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/provider.py, external/ipfs_datasets/tests/proof_context/test_v01_provider.py, artifacts/proof_carrying_context_engine/receipts/PCCE-008.json
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/contracts.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/provider.py, external/ipfs_datasets/tests/proof_context/test_v01_provider.py, artifacts/proof_carrying_context_engine/receipts/PCCE-008.json
- Conflict policy: This task owns only the new datasets port; changes to discovered canonical modules require a new migration task and non-overlap proof.
- Acceptance: Datasets exposes its canonical capabilities through a stable v0.1 port without duplicate authority or sibling-layout assumptions.

## PCCE-009 Remove kit v0.1 integration blockers

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_kit_py
- Owned paths: external/ipfs_kit/ipfs_kit_py/proof_context/artifacts.py, external/ipfs_kit/ipfs_kit_py/proof_context/state_store.py, external/ipfs_kit/tests/proof_context/test_v01_state_store.py, artifacts/proof_carrying_context_engine/receipts/PCCE-009.json
- Objective: Add the smallest kit-owned v0.1 port for immutable artifacts, state and receipt persistence, proof forests, generation-bearing CAS roots, WAL recovery, hermetic local storage, and optional IPFS transport.
- Depends on: PCCE-007
- Priority: P0
- Risk classification: critical-storage-integrity
- Execution mode: supervised bounded migration
- Allowed effects: Add narrow storage adapters and focused tests in the declared paths.
- Prohibited effects: Add another block store or WAL; require a daemon; translate real CIDs to pseudo-CIDs; accept corrupt, stale, ABA, or partially published state; broadly refactor kit.
- Acceptance criteria: Local mode is hermetic; bytes and authoritative CID agree; CAS detects stale/ABA writers; WAL replay yields one valid root; manifests verify transitively; optional IPFS is explicit and unavailable is not passed; imports need no sibling checkout.
- Required tests: python -m pytest -q external/ipfs_kit/tests/proof_context/test_v01_state_store.py
- Required evidence: Pre-change storage tests; crash/corruption/concurrency tests; canonical vectors; no-network trace; migration-map closure.
- Rollback procedure: Revert only the port commit; restore the prior CAS root through the canonical API if a test publication escaped; record partial_effect and invalidate dependents.
- Assigned worktree: pcce-PCCE-009
- Final result CID or artifact identity: pending task receipt and kit adapter tree identity
- Goal id: PCCE-G100
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_context/artifacts.py, external/ipfs_kit/ipfs_kit_py/proof_context/state_store.py, external/ipfs_kit/tests/proof_context/test_v01_state_store.py, artifacts/proof_carrying_context_engine/receipts/PCCE-009.json
- Validation: python -m pytest -q external/ipfs_kit/tests/proof_context/test_v01_state_store.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/kit-blockers
- Parallel lane: pcce-a-kit
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_kit/ipfs_kit_py/proof_context/artifacts.py, external/ipfs_kit/ipfs_kit_py/proof_context/state_store.py, external/ipfs_kit/tests/proof_context/test_v01_state_store.py, artifacts/proof_carrying_context_engine/receipts/PCCE-009.json
- Allowed paths: external/ipfs_kit/ipfs_kit_py/proof_context/artifacts.py, external/ipfs_kit/ipfs_kit_py/proof_context/state_store.py, external/ipfs_kit/tests/proof_context/test_v01_state_store.py, artifacts/proof_carrying_context_engine/receipts/PCCE-009.json
- Conflict policy: This task adapts the inventoried kit authority and may not introduce a second persistence implementation.
- Acceptance: Kit exposes one durable, recoverable, content-addressed v0.1 port with real CID and strict freshness semantics.

## PCCE-010 Remove accelerator v0.1 integration blockers

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/compatibility.py, external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py, artifacts/proof_carrying_context_engine/receipts/PCCE-010.json
- Objective: Add the smallest accelerator dependency/compatibility loader that resolves installed datasets, kit, and MCP++ contract capabilities without editable siblings, import-time installation, circular imports, mutable branches, or simulated production fallbacks.
- Depends on: PCCE-007
- Priority: P0
- Risk classification: high-runtime-integration
- Execution mode: supervised bounded migration
- Allowed effects: Add lazy capability discovery, compatibility checks, focused tests, and the unique receipt.
- Prohibited effects: Vendor sibling packages; mutate sys.path to arbitrary sources; install at import time; accept incompatible versions; convert unavailable dependencies into success; refactor unrelated supervisor code.
- Acceptance criteria: Cold import performs no network/process/filesystem mutation; capability loading uses installed package metadata and the compatibility matrix; absent or mismatched capabilities return typed unavailable/invalid; production rejects mocks, pseudo-CIDs, and mutable-ref dependencies.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py
- Required evidence: Import side-effect trace; clean environment resolution tests; incompatible/missing dependency tests; canonical-vector parity; migration-map closure.
- Rollback procedure: Revert only this dependency-loader commit and invalidate runtime tasks; do not alter external package installations.
- Assigned worktree: pcce-PCCE-010
- Final result CID or artifact identity: pending task receipt and accelerator compatibility tree identity
- Goal id: PCCE-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/compatibility.py, external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py, artifacts/proof_carrying_context_engine/receipts/PCCE-010.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/accelerate-blockers
- Parallel lane: pcce-a-accelerate
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/compatibility.py, external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py, artifacts/proof_carrying_context_engine/receipts/PCCE-010.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/compatibility.py, external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py, artifacts/proof_carrying_context_engine/receipts/PCCE-010.json
- Conflict policy: The loader composes installed authorities only; it cannot become a schema, semantic, persistence, or proof authority.
- Acceptance: Accelerator resolves the frozen v0.1 dependency surface cleanly and fails closed when any required installed authority is absent or incompatible.

## PCCE-011 Seal Epic A implementation and contract gate

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-011.json
- Objective: Revalidate exact repository/tree identities, inventory completeness, ownership, migrations, schema/vector parity, dependency imports, and blocker repairs before releasing the frozen contracts to runtime work.
- Depends on: PCCE-008, PCCE-009, PCCE-010
- Priority: P0
- Risk classification: release-gate-critical
- Execution mode: supervised acceptance gate
- Allowed effects: Run read-only cross-repository checks; write the Epic A gate and receipt.
- Prohibited effects: Repair implementation during the gate; waive mismatch; mutate contracts; report unavailable checks as passed.
- Acceptance criteria: All Epic A receipts verify and bind the expected commits/trees; inventories cover all reported systems; ownership violations are closed or explicitly external-blocked; schemas/vectors and installed ports agree; no editable sibling, recursive submodule, mutable branch, import installer, pseudo-CID, duplicate receipt, simulated-production success, missing metadata, incompatible schema, or circular import blocker remains on the supported path.
- Required tests: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py external/ipfs_datasets/tests/proof_context/test_v01_provider.py external/ipfs_kit/tests/proof_context/test_v01_state_store.py external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py
- Required evidence: Verified PCCE-001 through PCCE-010 receipt CIDs; exact source matrix; full gate logs; negative-test results; explicit go or documented no-go.
- Rollback procedure: Publish a failed gate, invalidate dependents, and return only the failing owner task to repair; never patch source from the gate worktree.
- Assigned worktree: pcce-PCCE-011
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json
- Goal id: PCCE-G100
- Outputs: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-011.json
- Validation: python -m pytest -q Mcp-Plus-Plus/tests-py/test_proof_context_v01_schemas.py Mcp-Plus-Plus/tests-py/test_proof_context_v01_vectors.py external/ipfs_datasets/tests/proof_context/test_v01_provider.py external/ipfs_kit/tests/proof_context/test_v01_state_store.py external/ipfs_accelerate/test/proof_context/test_v01_dependencies.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/a/freeze-gate
- Parallel lane: pcce-a-gate
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-011.json
- Allowed paths: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json, artifacts/proof_carrying_context_engine/receipts/PCCE-011.json
- Conflict policy: Gate is evidence-only; any mismatch blocks PCCE-020, PCCE-022, and PCCE-023 and reopens only its owning antecedent.
- Acceptance: Epic A produces a sealed, executable, implementation-derived v0.1 contract baseline or a documented no-go with no downstream release.

## PCCE-020 Implement the provider-neutral engine facade

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/facade.py, external/ipfs_accelerate/test/proof_context/test_facade.py, artifacts/proof_carrying_context_engine/receipts/PCCE-020.json
- Objective: Define ProofCarryingContextEngine.open and stable scan, status, plan, context-pack, route, run, verify, expand-context, assurance, seal, report, and resume methods over injected canonical ports.
- Depends on: PCCE-011
- Priority: P0
- Risk classification: high-public-api
- Execution mode: supervised runtime implementation
- Allowed effects: Add the facade and contract-focused tests in declared paths.
- Prohibited effects: Duplicate semantic, persistence, routing, verification, assurance, or sealing implementations; perform I/O at import; bind one model provider; mutate a canonical branch.
- Acceptance criteria: The facade is provider-neutral, typed, dependency-injected, ordinary-Python-repository compatible, cold-import safe, and exposes every required operation while preserving repository, task, run, patch, trace, contract-version, and artifact identities.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_facade.py
- Required evidence: Public signature snapshot; fake-port tests; import side-effect trace; Epic A contract/version binding.
- Rollback procedure: Revert the facade commit and invalidate lifecycle/CLI/adapters; no repository under evaluation may have been mutated by unit tests.
- Assigned worktree: pcce-PCCE-020
- Final result CID or artifact identity: pending facade API descriptor CID and task receipt
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/facade.py, external/ipfs_accelerate/test/proof_context/test_facade.py, artifacts/proof_carrying_context_engine/receipts/PCCE-020.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_facade.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/facade
- Parallel lane: pcce-b-facade
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/facade.py, external/ipfs_accelerate/test/proof_context/test_facade.py, artifacts/proof_carrying_context_engine/receipts/PCCE-020.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/facade.py, external/ipfs_accelerate/test/proof_context/test_facade.py, artifacts/proof_carrying_context_engine/receipts/PCCE-020.json
- Conflict policy: Facade composes frozen ports and owns no subsystem semantics; new cross-package requirements require a schema-versioned task.
- Acceptance: A stable ProofCarryingContextEngine surface exists independently of any concrete adapter or storage backend.

## PCCE-021 Implement the governed patch lifecycle coordinator

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/lifecycle.py, external/ipfs_accelerate/test/proof_context/test_lifecycle.py, artifacts/proof_carrying_context_engine/receipts/PCCE-021.json
- Objective: Implement one lifecycle from operator identity and repository resolution through semantic scan, invalidation, ContextPack/sufficiency, route, proposal, scope check, isolated apply, impact, incremental verification, escalation, assurance, seal, and disposition.
- Depends on: PCCE-020, PCCE-022, PCCE-023
- Priority: P0
- Risk classification: critical-governance
- Execution mode: supervised runtime implementation
- Allowed effects: Add the lifecycle coordinator and deterministic fake-port tests; use existing supervisor leases, fences, worktrees, cancellation, admission, retries, scheduling, and receipt facilities through ports.
- Prohibited effects: Let an adapter bypass a stage; accept an unsealed production patch; mutate protected/canonical branches; select tests or proofs independently of canonical planners; conceal a partial effect.
- Acceptance criteria: Every accepted production/supervised patch traverses the exact ordered lifecycle; each stage consumes and emits typed identity-bound artifacts; rejection, escalation, timeout, cancellation, unavailable, and partial-effect paths stop publication and persist evidence.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_lifecycle.py
- Required evidence: Stage-transition trace; success and every terminal-state tests; lease/fence/worktree receipts; bypass-rejection test; clean canonical-tree proof.
- Rollback procedure: Cancel active attempts, fence publishers, discard disposable worktrees, revert the coordinator commit, and preserve partial-effect receipts for dependent invalidation.
- Assigned worktree: pcce-PCCE-021
- Final result CID or artifact identity: pending lifecycle state-machine descriptor CID and task receipt
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/lifecycle.py, external/ipfs_accelerate/test/proof_context/test_lifecycle.py, artifacts/proof_carrying_context_engine/receipts/PCCE-021.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_lifecycle.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/lifecycle
- Parallel lane: pcce-b-lifecycle
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/lifecycle.py, external/ipfs_accelerate/test/proof_context/test_lifecycle.py, artifacts/proof_carrying_context_engine/receipts/PCCE-021.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/lifecycle.py, external/ipfs_accelerate/test/proof_context/test_lifecycle.py, artifacts/proof_carrying_context_engine/receipts/PCCE-021.json
- Conflict policy: This is the sole accepted-patch lifecycle authority; adapters and CLI may call it but may not reproduce or skip it.
- Acceptance: The required governed sequence is executable, restart-aware, and impossible to bypass for an accepted non-simulation result.

## PCCE-022 Implement production, supervised, evaluation, and simulation policy

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/policy.py, external/ipfs_accelerate/test/proof_context/test_policy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-022.json
- Objective: Define explicit closed runtime modes and promotion/admission rules that prevent simulated, replayed, stale, invalid, unavailable, pseudo-CID, unsigned-required, or unsealed evidence from entering production/supervised acceptance.
- Depends on: PCCE-011
- Priority: P0
- Risk classification: critical-trust
- Execution mode: supervised policy implementation
- Allowed effects: Add immutable policy records, admission checks, mode transitions, and focused negative tests.
- Prohibited effects: Silent fallback; mutable global policy; environment-variable promotion; treating replay as live quality; allowing an adapter to approve its own patch.
- Acceptance criteria: All four modes are explicit in every result; production and supervised reject all forbidden evidence; evaluation separates quality claims by live/replayed/simulated; simulation is watermarked transitively and has no direct promotion path.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_policy.py
- Required evidence: Policy descriptor CID; complete decision table; negative/promotion tests; frozen taxonomy compatibility.
- Rollback procedure: Revert the policy commit and invalidate all runtime results produced under it; never reinterpret old simulation evidence under a replacement policy.
- Assigned worktree: pcce-PCCE-022
- Final result CID or artifact identity: pending policy descriptor CID and task receipt
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/policy.py, external/ipfs_accelerate/test/proof_context/test_policy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-022.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_policy.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/modes-policy
- Parallel lane: pcce-b-policy
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/policy.py, external/ipfs_accelerate/test/proof_context/test_policy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-022.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/policy.py, external/ipfs_accelerate/test/proof_context/test_policy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-022.json
- Conflict policy: Frozen MCP++ taxonomies are wire authority; accelerator policy owns runtime admission only.
- Acceptance: Mode and promotion behavior is closed, deterministic, visible, and fail-closed at every production evidence boundary.

## PCCE-023 Implement typed failures and result state machine

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/errors.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/results.py, external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-023.json
- Objective: Project the frozen status/error taxonomy into typed exceptions and result records with legal transitions, retryability, partial-effect, human-review, and repair semantics.
- Depends on: PCCE-011
- Priority: P0
- Risk classification: high-control-flow
- Execution mode: supervised contract implementation
- Allowed effects: Add typed result/error modules and exhaustive transition tests.
- Prohibited effects: Return generic success dictionaries; collapse unavailable into failure/pass; expose arbitrary provider errors; add unversioned status values.
- Acceptance criteria: Every required status is represented exactly once; legal transitions are closed and deterministic; terminal results bind trace/run/task/repository/patch/evidence identities; errors are bounded/redacted and classify retry, escalation, review, and repair without claiming success.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py
- Required evidence: Exhaustive enum/transition table; schema round trips; unknown-status negative tests; redaction tests.
- Rollback procedure: Revert the typed-result commit and invalidate dependents; do not translate previously emitted results into a new taxonomy without migration.
- Assigned worktree: pcce-PCCE-023
- Final result CID or artifact identity: pending result-state descriptor CID and task receipt
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/errors.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/results.py, external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-023.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/results
- Parallel lane: pcce-b-results
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/errors.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/results.py, external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-023.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/errors.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/results.py, external/ipfs_accelerate/test/proof_context/test_result_taxonomy.py, artifacts/proof_carrying_context_engine/receipts/PCCE-023.json
- Conflict policy: Status wire values remain frozen; runtime types may add behavior but cannot widen accepted vocabulary.
- Acceptance: Runtime callers receive typed, identity-bound results and cannot mistake absence, simulation, partial effects, or failure for success.

## PCCE-024 Implement interruption recovery and idempotent resume

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/recovery.py, external/ipfs_accelerate/test/proof_context/test_recovery.py, artifacts/proof_carrying_context_engine/receipts/PCCE-024.json
- Objective: Persist and replay lifecycle checkpoints so resume after interruption reuses completed valid stages, repairs ambiguous effects, and never reinvokes a terminal adapter or publishes through an expired fence.
- Depends on: PCCE-021
- Priority: P0
- Risk classification: critical-recovery
- Execution mode: supervised runtime implementation
- Allowed effects: Add recovery/checkpoint coordination over canonical kit persistence and supervisor attempt identity; add crash-point tests.
- Prohibited effects: Create a second WAL; infer success from process exit alone; reuse stale receipts; duplicate external calls; ignore ambiguous apply/verification effects.
- Acceptance criteria: Every lifecycle boundary has an idempotency key and durable checkpoint; crash tests before/during/after patch apply, verification, and seal converge to one valid terminal state or repair_required; stale writers and expired leases cannot publish.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_recovery.py
- Required evidence: Crash matrix; replay trace; no-double-invocation proof; CAS/fence results; partial-effect repair receipts.
- Rollback procedure: Fence the attempt, discard disposable worktrees, restore only through canonical CAS/WAL recovery, revert recovery code, and preserve ambiguous-effect evidence.
- Assigned worktree: pcce-PCCE-024
- Final result CID or artifact identity: pending recovery protocol CID and task receipt
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/recovery.py, external/ipfs_accelerate/test/proof_context/test_recovery.py, artifacts/proof_carrying_context_engine/receipts/PCCE-024.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_recovery.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/recovery
- Parallel lane: pcce-b-recovery
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/recovery.py, external/ipfs_accelerate/test/proof_context/test_recovery.py, artifacts/proof_carrying_context_engine/receipts/PCCE-024.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/recovery.py, external/ipfs_accelerate/test/proof_context/test_recovery.py, artifacts/proof_carrying_context_engine/receipts/PCCE-024.json
- Conflict policy: Recovery replays canonical receipts/checkpoints only and never fabricates completion or bypasses current policy.
- Acceptance: Interrupted runs resume idempotently, fence stale publishers, surface ambiguity, and retain auditable partial effects.

## PCCE-025 Wire and qualify the stable runtime package surface

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/bootstrap.py, external/ipfs_accelerate/test/proof_context/test_runtime_integration.py, artifacts/proof_carrying_context_engine/runtime/runtime_api.json, artifacts/proof_carrying_context_engine/receipts/PCCE-025.json
- Objective: Wire the facade, lifecycle, modes, results, recovery, datasets port, and kit port into one stable lazy-loaded runtime package and prove the complete external-patch path on an ordinary temporary Git repository.
- Depends on: PCCE-020, PCCE-021, PCCE-022, PCCE-023, PCCE-024
- Priority: P0
- Risk classification: critical-integration
- Execution mode: supervised integration gate
- Allowed effects: Add package exports/bootstrap, integration tests, runtime API descriptor, and receipt.
- Prohibited effects: Add agent-specific logic; mutate the test repository canonical branch; bypass lifecycle stages; require sibling checkout placement, daemon, credentials, or network.
- Acceptance criteria: ProofCarryingContextEngine.open initializes a normal Python Git repository; scan/plan/external-patch/verify/assure/seal/report/resume work through frozen contracts and isolated worktrees; failure modes are typed; cold import is hermetic; runtime descriptor is stable.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_runtime_integration.py
- Required evidence: Full stage trace; clean source and disposable-worktree identities; receipt/seal CIDs; API descriptor; no-network/import trace; focused Epic B regression results.
- Rollback procedure: Revert wiring/exports, invalidate downstream adapter/CLI work, discard test worktrees, and preserve any failed integration receipts.
- Assigned worktree: pcce-PCCE-025
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/runtime/runtime_api.json
- Goal id: PCCE-G200
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/bootstrap.py, external/ipfs_accelerate/test/proof_context/test_runtime_integration.py, artifacts/proof_carrying_context_engine/runtime/runtime_api.json, artifacts/proof_carrying_context_engine/receipts/PCCE-025.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_runtime_integration.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/b/runtime-gate
- Parallel lane: pcce-b-gate
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/bootstrap.py, external/ipfs_accelerate/test/proof_context/test_runtime_integration.py, artifacts/proof_carrying_context_engine/runtime/runtime_api.json, artifacts/proof_carrying_context_engine/receipts/PCCE-025.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/bootstrap.py, external/ipfs_accelerate/test/proof_context/test_runtime_integration.py, artifacts/proof_carrying_context_engine/runtime/runtime_api.json, artifacts/proof_carrying_context_engine/receipts/PCCE-025.json
- Conflict policy: This task alone wires public exports; component owners must not concurrently edit package exports.
- Acceptance: One stable, provider-neutral runtime package executes the governed external-patch vertical slice and fails closed under all invalid evidence cases.

## PCCE-030 Define the provider-neutral coding-agent adapter contract

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/base.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/models.py, external/ipfs_accelerate/test/proof_context/adapters/test_base.py, artifacts/proof_carrying_context_engine/receipts/PCCE-030.json
- Objective: Define CodingAgentAdapter and PatchProposal contracts for provider, model/revision, route tier, patch, declared files, token/cache counts, latency, cost, response identity, cancellation, and live/replayed/simulated provenance.
- Depends on: PCCE-025
- Priority: P0
- Risk classification: high-adapter-boundary
- Execution mode: supervised contract implementation
- Allowed effects: Add protocols, immutable records, validators, and focused contract tests.
- Prohibited effects: Invoke a provider; approve a patch; expose canonical-branch authority; accept undeclared files, unbounded patches/logs, hidden evaluation data, or provenance-free results.
- Acceptance criteria: The interface consumes frozen ContextPack, TaskSpecification, and ModelRouteDecision identities; proposals are bounded, schema-valid, cancellable, cost/token explicit, and cannot self-approve or claim live status without live evidence.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_base.py
- Required evidence: Protocol signature; schema round trips; invalid-scope/provenance tests; cancellation contract; contract CID.
- Rollback procedure: Revert the adapter contract before concrete adapters merge; after use, version the interface and invalidate dependent adapter receipts.
- Assigned worktree: pcce-PCCE-030
- Final result CID or artifact identity: pending adapter interface descriptor CID and task receipt
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/base.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/models.py, external/ipfs_accelerate/test/proof_context/adapters/test_base.py, artifacts/proof_carrying_context_engine/receipts/PCCE-030.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_base.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/adapter-contract
- Parallel lane: pcce-c-contract
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/base.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/models.py, external/ipfs_accelerate/test/proof_context/adapters/test_base.py, artifacts/proof_carrying_context_engine/receipts/PCCE-030.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/base.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/models.py, external/ipfs_accelerate/test/proof_context/adapters/test_base.py, artifacts/proof_carrying_context_engine/receipts/PCCE-030.json
- Conflict policy: Concrete adapters depend on this frozen interface and own disjoint modules; interface changes require explicit versioning.
- Acceptance: One bounded, provider-neutral proposal interface carries complete identity, usage, cost, cancellation, and provenance data.

## PCCE-031 Implement the Codex adapter

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/codex.py, external/ipfs_accelerate/test/proof_context/adapters/test_codex.py, artifacts/proof_carrying_context_engine/receipts/PCCE-031.json
- Objective: Implement a Codex proposal adapter using the supported installed integration mechanism discovered at implementation time, consuming only the admitted ContextPack/task/route and returning a structured proposal.
- Depends on: PCCE-030
- Priority: P0
- Risk classification: critical-external-agent
- Execution mode: supervised adapter implementation
- Allowed effects: Add the adapter and fake-client/recorded transport tests; make an explicitly permitted bounded provider call only in an opt-in integration test.
- Prohibited effects: Grant canonical-branch or policy authority; expose hidden evaluation data or implicit credentials; use unrestricted filesystem scope; self-approve; claim live usage/cost from a replay; silently substitute another mechanism.
- Acceptance criteria: Repository/task/pack/route identities survive request and response; file scope is constrained; cancellation and bounded logs work; model/revision/tokens/cache/latency/cost/response identity/provenance are recorded; unavailable supported integration returns unavailable.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_codex.py
- Required evidence: Supported-mechanism version probe; redacted request/response fixtures; cancellation/scope tests; live integration receipt if credentials and explicit permit exist, otherwise a truthful unavailable evidence row.
- Rollback procedure: Cancel live calls, revoke task-scoped temporary resources, revert adapter code, and preserve provider-side request identities/costs in the failure receipt.
- Assigned worktree: pcce-PCCE-031
- Final result CID or artifact identity: pending Codex adapter descriptor CID and task receipt
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/codex.py, external/ipfs_accelerate/test/proof_context/adapters/test_codex.py, artifacts/proof_carrying_context_engine/receipts/PCCE-031.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_codex.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/codex
- Parallel lane: pcce-c-codex
- Resource class: network-small
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/codex.py, external/ipfs_accelerate/test/proof_context/adapters/test_codex.py, artifacts/proof_carrying_context_engine/receipts/PCCE-031.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/codex.py, external/ipfs_accelerate/test/proof_context/adapters/test_codex.py, artifacts/proof_carrying_context_engine/receipts/PCCE-031.json
- Conflict policy: Provider access requires an explicit task-scoped permit and allowlist; all acceptance remains lifecycle authority outside the adapter.
- Acceptance: Codex can propose a bounded structured patch from a ContextPack without gaining verification, approval, or canonical-branch authority.

## PCCE-032 Implement the bounded command adapter

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/command.py, external/ipfs_accelerate/test/proof_context/adapters/test_command.py, artifacts/proof_carrying_context_engine/receipts/PCCE-032.json
- Objective: Invoke a locally configured coding agent through an executable allowlist, argument-list process API, isolated environment, timeout/cancellation, bounded logs, and structured output decoder.
- Depends on: PCCE-030
- Priority: P0
- Risk classification: critical-subprocess
- Execution mode: supervised adapter implementation
- Allowed effects: Add bounded subprocess adapter and hermetic fake-executable tests.
- Prohibited effects: Shell-string interpolation; arbitrary executable/path selection; inherited credentials or environment; unlimited logs/process trees; network by default; canonical-branch mutation.
- Acceptance criteria: Only exact allowlisted executables run via argv; environment and cwd are isolated; timeout/cancel terminates descendants; stdout/stderr are bounded/redacted; structured output is strict; command injection and malformed proposal cases fail closed.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_command.py
- Required evidence: Process argv/event receipts; injection matrix; timeout/descendant cleanup tests; environment/credential audit; output-bound tests.
- Rollback procedure: Terminate the captured process group, discard task worktree, revert adapter code, and retain partial-effect/process receipts.
- Assigned worktree: pcce-PCCE-032
- Final result CID or artifact identity: pending command adapter descriptor CID and task receipt
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/command.py, external/ipfs_accelerate/test/proof_context/adapters/test_command.py, artifacts/proof_carrying_context_engine/receipts/PCCE-032.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_command.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/command
- Parallel lane: pcce-c-command
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/command.py, external/ipfs_accelerate/test/proof_context/adapters/test_command.py, artifacts/proof_carrying_context_engine/receipts/PCCE-032.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/command.py, external/ipfs_accelerate/test/proof_context/adapters/test_command.py, artifacts/proof_carrying_context_engine/receipts/PCCE-032.json
- Conflict policy: Executable and environment policy is explicit immutable input; no adapter-controlled widening is accepted.
- Acceptance: A generic local agent can be called safely through argv and strict structured output with bounded, cancellable effects.

## PCCE-033 Implement the deterministic recorded-response adapter

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/replay.py, external/ipfs_accelerate/test/proof_context/adapters/test_replay.py, artifacts/proof_carrying_context_engine/receipts/PCCE-033.json
- Objective: Provide deterministic offline replay keyed to exact ContextPack, task, route, adapter, and response artifact identities for unit tests, CI, benchmark reproduction, and offline development.
- Depends on: PCCE-030
- Priority: P0
- Risk classification: medium-evidence-provenance
- Execution mode: supervised adapter implementation
- Allowed effects: Add replay adapter, fixture decoder, and deterministic tests.
- Prohibited effects: Mark replay live; alter recorded usage/cost; accept an identity mismatch; promote replay into live-model quality evidence; invoke network/process providers.
- Acceptance criteria: Byte-identical inputs produce identical proposals; mismatched pack/task/route/provider/revision fails; output is always replayed; fixture CIDs verify; no external effect occurs.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_replay.py
- Required evidence: Determinism results; no-I/O trace; mismatch negatives; fixture/response CIDs; provenance schema round trips.
- Rollback procedure: Revert replay code and invalidate only replay-derived tasks/results; live evidence is unaffected.
- Assigned worktree: pcce-PCCE-033
- Final result CID or artifact identity: pending replay adapter descriptor CID and task receipt
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/replay.py, external/ipfs_accelerate/test/proof_context/adapters/test_replay.py, artifacts/proof_carrying_context_engine/receipts/PCCE-033.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_replay.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/replay
- Parallel lane: pcce-c-replay
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/replay.py, external/ipfs_accelerate/test/proof_context/adapters/test_replay.py, artifacts/proof_carrying_context_engine/receipts/PCCE-033.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/replay.py, external/ipfs_accelerate/test/proof_context/adapters/test_replay.py, artifacts/proof_carrying_context_engine/receipts/PCCE-033.json
- Conflict policy: Replay provenance is immutable and transitively labeled; policy may exclude it but cannot relabel it.
- Acceptance: Deterministic replay supports tests and reproduction while remaining categorically excluded from live-model claims.

## PCCE-034 Implement the external patch adapter

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/external_patch.py, external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py, artifacts/proof_carrying_context_engine/receipts/PCCE-034.json
- Objective: Accept an externally created patch as an identity-bound proposal while preserving the same scope, impact, verification, assurance, sealing, and human-review lifecycle requirements.
- Depends on: PCCE-030
- Priority: P0
- Risk classification: high-untrusted-input
- Execution mode: supervised adapter implementation
- Allowed effects: Add strict patch ingestion/normalization and focused tests; no patch application occurs inside the adapter.
- Prohibited effects: Trust declared files over parsed patch paths; accept binary/path traversal/oversized input outside policy; bypass ContextPack or lifecycle; infer external approval.
- Acceptance criteria: Patch bytes have a real artifact identity; paths and declared files agree and are repository-relative; provenance is external; invalid encodings/traversal/scope escape fail; valid proposals enter the ordinary governed lifecycle without special acceptance.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py
- Required evidence: Patch-parser vectors; traversal/scope negatives; artifact CID; lifecycle handoff test; no-apply trace.
- Rollback procedure: Revert ingestion code and delete only unmerged disposable proposal artifacts; preserve rejected-input digests in the receipt without sensitive bodies.
- Assigned worktree: pcce-PCCE-034
- Final result CID or artifact identity: pending external-patch adapter descriptor CID and task receipt
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/external_patch.py, external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py, artifacts/proof_carrying_context_engine/receipts/PCCE-034.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/external-patch
- Parallel lane: pcce-c-external
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/external_patch.py, external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py, artifacts/proof_carrying_context_engine/receipts/PCCE-034.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/external_patch.py, external/ipfs_accelerate/test/proof_context/adapters/test_external_patch.py, artifacts/proof_carrying_context_engine/receipts/PCCE-034.json
- Conflict policy: Adapter validates and packages bytes only; lifecycle owns worktree application and acceptance.
- Acceptance: Externally generated patches receive no trust shortcut and traverse the same governed verification and sealing path.

## PCCE-035 Wire the adapter registry and conformance gate

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/registry.py, external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py, artifacts/proof_carrying_context_engine/adapters/conformance.json, artifacts/proof_carrying_context_engine/receipts/PCCE-035.json
- Objective: Register Codex, command, replay, and external-patch adapters through explicit configuration and prove a shared conformance suite without adapter-controlled approval or authority widening.
- Depends on: PCCE-031, PCCE-032, PCCE-033, PCCE-034
- Priority: P0
- Risk classification: critical-adapter-integration
- Execution mode: supervised integration gate
- Allowed effects: Add registry/exports, conformance tests, conformance artifact, and receipt.
- Prohibited effects: Dynamic arbitrary import; implicit credential discovery; default shell execution; live/replay provenance conflation; lifecycle bypass.
- Acceptance criteria: Registry names/configuration are closed; every adapter satisfies identity/scope/cancellation/provenance/bounds contracts; unavailable adapters remain unavailable; lifecycle is the sole consumer that may advance proposals toward acceptance.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py
- Required evidence: All adapter task receipts; shared conformance matrix; registry descriptor CID; negative authority tests; optional-live result labeled accurately.
- Rollback procedure: Revert registry/exports and conformance artifact; leave individual adapters installed but unreachable until a valid registry is restored.
- Assigned worktree: pcce-PCCE-035
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/adapters/conformance.json
- Goal id: PCCE-G300
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/registry.py, external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py, artifacts/proof_carrying_context_engine/adapters/conformance.json, artifacts/proof_carrying_context_engine/receipts/PCCE-035.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/c/adapter-gate
- Parallel lane: pcce-c-gate
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/registry.py, external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py, artifacts/proof_carrying_context_engine/adapters/conformance.json, artifacts/proof_carrying_context_engine/receipts/PCCE-035.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/adapters/registry.py, external/ipfs_accelerate/test/proof_context/adapters/test_conformance.py, artifacts/proof_carrying_context_engine/adapters/conformance.json, artifacts/proof_carrying_context_engine/receipts/PCCE-035.json
- Conflict policy: Registry is an allowlist over concrete adapters; plugin-style arbitrary imports are prohibited for v0.1.
- Acceptance: All supported proposal sources share one strict adapter boundary and none can approve, apply, verify, or seal its own output.

## PCCE-040 Implement CLI application and repository-state commands

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/app.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/state_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-040.json
- Objective: Implement the CLI parser/context plus init, scan, status, and plan commands as thin calls into the stable runtime with explicit repository, policy, task, correlation, and output-mode arguments.
- Depends on: PCCE-025
- Priority: P0
- Risk classification: high-user-surface
- Execution mode: supervised CLI implementation
- Allowed effects: Add CLI application/state command modules, isolated-repository tests, and receipt.
- Prohibited effects: Duplicate lifecycle logic; mutate outside the selected repository state directory; infer current directory silently when an explicit repository is required by policy; emit untyped success.
- Acceptance criteria: Commands initialize an ordinary Python Git repository, scan/persist semantic state, show typed status, and produce a proof-aware plan; help/argument errors are stable; no command bypasses runtime policy or starts work at import.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py
- Required evidence: CLI invocation transcript; exit-code table subset; state/plan artifact CIDs; clean repository/worktree proof; import trace.
- Rollback procedure: Revert CLI state modules, remove only disposable test repositories, and retain command receipts; runtime state is not rewritten.
- Assigned worktree: pcce-PCCE-040
- Final result CID or artifact identity: pending state-command descriptor CID and task receipt
- Goal id: PCCE-G400
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/app.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/state_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-040.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/d/state-cli
- Parallel lane: pcce-d-state
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/app.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/state_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-040.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/app.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/state_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_state_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-040.json
- Conflict policy: CLI is a presentation/call layer only; runtime ports and contracts remain authoritative.
- Acceptance: init, scan, status, and plan are stable, scriptable runtime calls with no hidden authority or side effects.

## PCCE-041 Implement CLI run, verify, and resume commands

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/execution_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-041.json
- Objective: Implement run with explicit adapter/task, verify by run or patch identity, and resume by run identity through the governed lifecycle and adapter registry.
- Depends on: PCCE-035, PCCE-040
- Priority: P0
- Risk classification: critical-execution-surface
- Execution mode: supervised CLI implementation
- Allowed effects: Add execution commands and fake/replay/external-patch CLI tests in disposable repositories.
- Prohibited effects: Apply directly to the canonical branch; bypass scope, verification, assurance, seal, or review; invoke unregistered adapters; retry indefinitely; hide partial effects.
- Acceptance criteria: run accepts Codex/command/replay/external-patch only through registry policy; verify cannot validate the wrong patch/run; resume is idempotent; cancellation/timeouts propagate; every terminal status maps to stable output and exit code.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py
- Required evidence: Full command transcripts; adapter and lifecycle receipt CIDs; cancellation/resume tests; clean canonical-tree checks; exit-code results.
- Rollback procedure: Cancel/fence active runs, discard disposable worktrees, revert execution commands, and preserve attempt/partial-effect receipts.
- Assigned worktree: pcce-PCCE-041
- Final result CID or artifact identity: pending execution-command descriptor CID and task receipt
- Goal id: PCCE-G400
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/execution_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-041.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/d/execution-cli
- Parallel lane: pcce-d-execution
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/execution_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-041.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/execution_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_execution_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-041.json
- Conflict policy: Execution commands delegate exclusively to the public runtime and registry; direct patch/worktree operations are forbidden.
- Acceptance: run, verify, and resume expose the complete governed lifecycle without adding a CLI bypass.

## PCCE-042 Implement CLI evidence and escalation commands

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/evidence_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-042.json
- Objective: Implement expand-context, explain-impact, assurance, seal, and report commands as governed operations on an exact existing run identity.
- Depends on: PCCE-025, PCCE-040
- Priority: P0
- Risk classification: high-evidence-surface
- Execution mode: supervised CLI implementation
- Allowed effects: Add evidence/escalation commands and deterministic integration tests using existing run artifacts.
- Prohibited effects: Alter evidence in place; seal failed/unavailable/simulated production evidence; estimate impact without labeling; expand with hidden benchmark answers; overwrite a prior seal.
- Acceptance criteria: Each command resolves one run/repository/patch identity, verifies parents and freshness, emits new immutable artifacts, records context expansion/frontier escalation, and rejects wrong-parent, stale, failed, or unavailable evidence.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py
- Required evidence: Command transcripts; impact/context/assurance/seal/report CIDs; stale/wrong-parent negatives; immutable-parent proof.
- Rollback procedure: Revert commands and abandon unmerged derived artifacts; never delete or rewrite already content-addressed evidence.
- Assigned worktree: pcce-PCCE-042
- Final result CID or artifact identity: pending evidence-command descriptor CID and task receipt
- Goal id: PCCE-G400
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/evidence_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-042.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/d/evidence-cli
- Parallel lane: pcce-d-evidence
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/evidence_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-042.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/evidence_commands.py, external/ipfs_accelerate/test/proof_context/cli/test_evidence_commands.py, artifacts/proof_carrying_context_engine/receipts/PCCE-042.json
- Conflict policy: Evidence commands append identity-bound artifacts only; canonical producers remain authoritative.
- Acceptance: Users can explicitly inspect, expand, assure, seal, and report a run with strict freshness and parent binding.

## PCCE-043 Implement stable JSON output, exit codes, and human report rendering

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/output.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/report.py, external/ipfs_accelerate/test/proof_context/cli/test_output.py, artifacts/proof_carrying_context_engine/cli/output_schema.json, artifacts/proof_carrying_context_engine/receipts/PCCE-043.json
- Objective: Define stable machine output and exit-code mappings plus a human patch report covering task, revision, routing, context, changes, verification/proof reuse, assurance, escalation, costs, review, receipts, and seal.
- Depends on: PCCE-025
- Priority: P0
- Risk classification: high-observability
- Execution mode: supervised reporting implementation
- Allowed effects: Add renderers, stable output schema, focused snapshots, and receipt.
- Prohibited effects: Emit secrets or unbounded logs/source; call estimated savings observed; collapse unavailable/failure/simulation into exit zero; omit artifact and trace identities.
- Acceptance criteria: Every command result has schema version, status, exit code, trace/correlation ID, repository/task/run/patch identities, and artifact CIDs; human report contains every required field and labels estimates/baselines/missing evidence honestly.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_output.py; python -m json.tool artifacts/proof_carrying_context_engine/cli/output_schema.json
- Required evidence: JSON-schema CID; golden human reports for pass/fail/unavailable/simulated; exit-code matrix; redaction and bounded-output tests.
- Rollback procedure: Revert renderer/schema commit and invalidate CLI outputs generated under it; underlying runtime artifacts remain immutable.
- Assigned worktree: pcce-PCCE-043
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/cli/output_schema.json
- Goal id: PCCE-G400
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/output.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/report.py, external/ipfs_accelerate/test/proof_context/cli/test_output.py, artifacts/proof_carrying_context_engine/cli/output_schema.json, artifacts/proof_carrying_context_engine/receipts/PCCE-043.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_output.py && python -m json.tool artifacts/proof_carrying_context_engine/cli/output_schema.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/d/output
- Parallel lane: pcce-d-output
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/output.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/report.py, external/ipfs_accelerate/test/proof_context/cli/test_output.py, artifacts/proof_carrying_context_engine/cli/output_schema.json, artifacts/proof_carrying_context_engine/receipts/PCCE-043.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/output.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/report.py, external/ipfs_accelerate/test/proof_context/cli/test_output.py, artifacts/proof_carrying_context_engine/cli/output_schema.json, artifacts/proof_carrying_context_engine/receipts/PCCE-043.json
- Conflict policy: Output projection cannot change semantic status or artifact identity; schema changes require explicit versioning.
- Acceptance: Human and machine consumers receive complete, stable, identity-bound reports with truthful cost and evidence labeling.

## PCCE-044 Wire and qualify the complete CLI

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__main__.py, external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py, external/ipfs_accelerate/docs/guides/proof-context-cli.md, artifacts/proof_carrying_context_engine/cli/command_manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-044.json
- Objective: Wire all CLI commands and renderers into one python -m entrypoint, document exact examples, and qualify the full replay/external-patch workflow before packaging adds the proof-context console script.
- Depends on: PCCE-035, PCCE-041, PCCE-042, PCCE-043
- Priority: P0
- Risk classification: critical-cli-integration
- Execution mode: supervised integration gate
- Allowed effects: Add CLI exports/entrypoint, end-to-end tests, user guide, command manifest, and receipt.
- Prohibited effects: Edit packaging metadata; require live provider credentials; skip failed required commands; hide exit codes; modify canonical branches or protected control docs.
- Acceptance criteria: All required command equivalents are discoverable; JSON and human modes work; replay and external-patch good/bad flows traverse governance; resume survives injected interruption; documented commands execute from a clean checkout through python -m.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py
- Required evidence: Command manifest CID; full transcripts and exit codes; report/seal CIDs; documentation execution test; clean repository proof.
- Rollback procedure: Revert CLI wiring/docs and invalidate the command manifest; retain lower-level runtime and command modules for repair.
- Assigned worktree: pcce-PCCE-044
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/cli/command_manifest.json
- Goal id: PCCE-G400
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__main__.py, external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py, external/ipfs_accelerate/docs/guides/proof-context-cli.md, artifacts/proof_carrying_context_engine/cli/command_manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-044.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/d/cli-gate
- Parallel lane: pcce-d-gate
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__main__.py, external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py, external/ipfs_accelerate/docs/guides/proof-context-cli.md, artifacts/proof_carrying_context_engine/cli/command_manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-044.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/proof_context/cli/__main__.py, external/ipfs_accelerate/test/proof_context/cli/test_cli_end_to_end.py, external/ipfs_accelerate/docs/guides/proof-context-cli.md, artifacts/proof_carrying_context_engine/cli/command_manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-044.json
- Conflict policy: This task alone wires CLI exports; packaging entry points remain PCCE-052 ownership.
- Acceptance: One documented, stable CLI exposes the complete governed engine in human and machine-readable modes.

## PCCE-050 Package the datasets v0.1 semantic provider

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/__init__.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-050.json
- Objective: Export and package the datasets proof-context provider from an immutable wheel/sdist without editable installs, sibling paths, mutable branch dependencies, or eager heavy optional dependencies.
- Depends on: PCCE-044
- Priority: P0
- Risk classification: high-packaging
- Execution mode: supervised packaging implementation
- Allowed effects: Add package export and minimal metadata changes, build wheel/sdist, run clean-wheel tests, and write the receipt.
- Prohibited effects: Vendor sibling repos; add recursive submodules; pin mutable main; pull all theorem/model/browser dependencies into core; install on import.
- Acceptance criteria: Wheel and sdist build reproducibly; installed package exposes the v0.1 provider and metadata; core import is hermetic; canonical existing extras remain compatible; source-tree absence does not break imports.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/test_install_profile.py; python -m build external/ipfs_datasets
- Required evidence: Wheel/sdist hashes; clean virtual-environment transcript; dependency metadata; import/no-network trace; package contents manifest.
- Rollback procedure: Revert only datasets packaging/export changes, withdraw unpromoted artifacts, and invalidate dependent locks; do not alter existing released artifacts.
- Assigned worktree: pcce-PCCE-050
- Final result CID or artifact identity: pending datasets wheel/sdist identities and task receipt
- Goal id: PCCE-G500
- Outputs: external/ipfs_datasets/ipfs_datasets_py/proof_context/__init__.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-050.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/test_install_profile.py && python -m build external/ipfs_datasets
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/package-datasets
- Parallel lane: pcce-e-datasets
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/proof_context/__init__.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-050.json
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/__init__.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-050.json
- Conflict policy: Datasets packaging owns only its repository metadata/export; accelerator extras are PCCE-052 ownership.
- Acceptance: The canonical datasets capability is consumable from immutable package artifacts in a clean environment.

## PCCE-051 Package the kit v0.1 persistence provider

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_kit_py
- Owned paths: external/ipfs_kit/ipfs_kit_py/proof_context/__init__.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-051.json
- Objective: Export and package the kit proof-context storage provider from immutable wheel/sdist artifacts with hermetic local storage in core and optional IPFS transport isolated behind an extra.
- Depends on: PCCE-044
- Priority: P0
- Risk classification: high-packaging-integrity
- Execution mode: supervised packaging implementation
- Allowed effects: Add package export and minimal metadata changes, build artifacts, run clean-wheel/local-storage tests, and write receipt.
- Prohibited effects: Require daemon/network in core; vendor siblings; use editable install or mutable branch; make optional backends import-time requirements.
- Acceptance criteria: Wheel/sdist install without source siblings; local CAS/WAL/receipt paths work in a temporary directory; optional IPFS remains explicit; import does no I/O; metadata exposes exact compatible versions.
- Required tests: python -m pytest -q external/ipfs_kit/tests/proof_context/test_install_profile.py; python -m build external/ipfs_kit
- Required evidence: Artifact hashes; clean environment transcript; local-store test receipts; no-daemon/no-network trace; package manifest.
- Rollback procedure: Revert kit packaging/export changes, withdraw only unpromoted artifacts, and invalidate dependent locks.
- Assigned worktree: pcce-PCCE-051
- Final result CID or artifact identity: pending kit wheel/sdist identities and task receipt
- Goal id: PCCE-G500
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_context/__init__.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-051.json
- Validation: python -m pytest -q external/ipfs_kit/tests/proof_context/test_install_profile.py && python -m build external/ipfs_kit
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/package-kit
- Parallel lane: pcce-e-kit
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_kit/ipfs_kit_py/proof_context/__init__.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-051.json
- Allowed paths: external/ipfs_kit/ipfs_kit_py/proof_context/__init__.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/tests/proof_context/test_install_profile.py, artifacts/proof_carrying_context_engine/receipts/PCCE-051.json
- Conflict policy: Kit packaging owns only kit metadata/export and must keep network storage optional.
- Acceptance: The canonical persistence capability installs cleanly and provides a hermetic local default without sibling placement.

## PCCE-052 Package runtime profiles and console entry point

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/test/proof_context/test_install_profiles.py, artifacts/proof_carrying_context_engine/receipts/PCCE-052.json
- Objective: Package the accelerator runtime and proof-context console script with supported core, verification, Codex adapter, already-supported local-model adapter, and full-evaluation profiles.
- Depends on: PCCE-044
- Priority: P0
- Risk classification: critical-distribution
- Execution mode: supervised packaging implementation
- Allowed effects: Add minimal package metadata/extras/entrypoint changes, build wheel/sdist, run profile resolution tests, and write receipt.
- Prohibited effects: Add a new provider; include every model/browser/prover/storage backend in core; use editable/sibling/mutable-main dependencies; run installers on import.
- Acceptance criteria: Core installs datasets/kit runtime minima only; verification/Codex/local-model/evaluation extras are separated; local-model extra exists only if inventory proves support; proof-context entrypoint resolves; every dependency is version-bounded and immutable-artifact compatible.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_install_profiles.py; python -m build external/ipfs_accelerate
- Required evidence: Wheel/sdist hashes; extras dependency graph; clean environment transcripts for each supported profile; entrypoint smoke; absent-optional-dependency tests.
- Rollback procedure: Revert accelerator metadata/entrypoint changes, withdraw unpromoted artifacts, and invalidate environment locks.
- Assigned worktree: pcce-PCCE-052
- Final result CID or artifact identity: pending accelerator wheel/sdist identities and task receipt
- Goal id: PCCE-G500
- Outputs: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/test/proof_context/test_install_profiles.py, artifacts/proof_carrying_context_engine/receipts/PCCE-052.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_install_profiles.py && python -m build external/ipfs_accelerate
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/package-runtime
- Parallel lane: pcce-e-runtime
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/test/proof_context/test_install_profiles.py, artifacts/proof_carrying_context_engine/receipts/PCCE-052.json
- Allowed paths: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/test/proof_context/test_install_profiles.py, artifacts/proof_carrying_context_engine/receipts/PCCE-052.json
- Conflict policy: This task is the sole owner of accelerator packaging metadata for the board; profile composition cannot widen runtime authority.
- Acceptance: Immutable accelerator artifacts expose a lean core and explicit optional profiles with a working proof-context console entry point.

## PCCE-053 Produce locks, hashes, SBOM, and environment manifest

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: external/ipfs_accelerate/packaging/proof_context/locks, external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py, artifacts/proof_carrying_context_engine/environment/dependency_locks.json, artifacts/proof_carrying_context_engine/environment/artifact_hashes.json, artifacts/proof_carrying_context_engine/environment/sbom.spdx.json, artifacts/proof_carrying_context_engine/environment/manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-053.json
- Objective: Resolve reproducible dependency locks and hashes for supported profiles and produce an SBOM/environment manifest declaring exact source commits, package artifacts, Python versions, operating systems, tools, and optional capabilities.
- Depends on: PCCE-050, PCCE-051, PCCE-052
- Priority: P0
- Risk classification: critical-supply-chain
- Execution mode: supervised reproducibility implementation
- Allowed effects: Add lock files and a deterministic manifest builder; write generated environment evidence and receipt.
- Prohibited effects: Use mutable VCS refs, unhashed direct URLs, ambient editable packages, undeclared indexes, credentials, or platform claims without a tested runner.
- Acceptance criteria: Locks are profile/platform explicit and hash-bound; SBOM covers direct/transitive distributions and licenses; manifest pins sources/artifacts/toolchain; regeneration is deterministic; unsupported OS/Python combinations are explicit rather than passed.
- Required tests: python external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py --check; python -m json.tool artifacts/proof_carrying_context_engine/environment/sbom.spdx.json; python -m json.tool artifacts/proof_carrying_context_engine/environment/manifest.json
- Required evidence: Input artifact hashes; lock resolver receipts; deterministic two-run comparison; SBOM validation; declared support matrix.
- Rollback procedure: Revert lock/builder changes and invalidate generated environment artifacts; do not alter published package artifacts.
- Assigned worktree: pcce-PCCE-053
- Final result CID or artifact identity: pending environment-manifest and SBOM CIDs
- Goal id: PCCE-G500
- Outputs: external/ipfs_accelerate/packaging/proof_context/locks, external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py, artifacts/proof_carrying_context_engine/environment/dependency_locks.json, artifacts/proof_carrying_context_engine/environment/artifact_hashes.json, artifacts/proof_carrying_context_engine/environment/sbom.spdx.json, artifacts/proof_carrying_context_engine/environment/manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-053.json
- Validation: python external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py --check && python -m json.tool artifacts/proof_carrying_context_engine/environment/sbom.spdx.json && python -m json.tool artifacts/proof_carrying_context_engine/environment/manifest.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/reproducibility
- Parallel lane: pcce-e-environment
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/packaging/proof_context/locks, external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py, artifacts/proof_carrying_context_engine/environment/dependency_locks.json, artifacts/proof_carrying_context_engine/environment/artifact_hashes.json, artifacts/proof_carrying_context_engine/environment/sbom.spdx.json, artifacts/proof_carrying_context_engine/environment/manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-053.json
- Allowed paths: external/ipfs_accelerate/packaging/proof_context/locks, external/ipfs_accelerate/scripts/proof_context/build_environment_manifest.py, artifacts/proof_carrying_context_engine/environment/dependency_locks.json, artifacts/proof_carrying_context_engine/environment/artifact_hashes.json, artifacts/proof_carrying_context_engine/environment/sbom.spdx.json, artifacts/proof_carrying_context_engine/environment/manifest.json, artifacts/proof_carrying_context_engine/receipts/PCCE-053.json
- Conflict policy: Generated identities derive only from admitted package artifacts and declared resolvers; no post hoc lock edits.
- Acceptance: Supported environments are reproducible, hash-bound, inventoried, and honest about platform and optional-capability limits.

## PCCE-054 Add clean-install CI and optional container profile

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/.github/workflows/proof-context-clean-install.yml, external/ipfs_accelerate/docker/proof-context/Dockerfile, external/ipfs_accelerate/scripts/proof_context/test_clean_install.py, external/ipfs_accelerate/test/proof_context/test_clean_install.py, artifacts/proof_carrying_context_engine/receipts/PCCE-054.json
- Objective: Test installation solely from built immutable artifacts in fresh environments and provide a pinned optional container build for the supported core/verification profile.
- Depends on: PCCE-053
- Priority: P0
- Risk classification: high-installation
- Execution mode: supervised CI/container implementation
- Allowed effects: Add required clean-install workflow, pinned Dockerfile, clean-install harness/tests, and receipt; build disposable environments/images.
- Prohibited effects: Install from source siblings or editable paths; use mutable base tags without digest; download undeclared dependencies; mark unavailable builds passed; use continue-on-error or equivalent.
- Acceptance criteria: Each supported Python/profile matrix installs from wheels with hashes, imports, runs CLI smoke, and proves no sibling requirement; container uses pinned base and non-root runtime where supported; any unsupported runner is explicitly failed/no-go.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_clean_install.py; python external/ipfs_accelerate/scripts/proof_context/test_clean_install.py --artifacts artifacts/proof_carrying_context_engine/environment/artifact_hashes.json
- Required evidence: Fresh-environment transcripts; installed-distribution hashes; workflow result; container digest/build log or explicit unsupported no-go; no-source-path trace.
- Rollback procedure: Revert CI/container/harness changes and delete only disposable environments/images; retain failed install logs and immutable packages.
- Assigned worktree: pcce-PCCE-054
- Final result CID or artifact identity: pending clean-install matrix and optional image digest
- Goal id: PCCE-G500
- Outputs: external/ipfs_accelerate/.github/workflows/proof-context-clean-install.yml, external/ipfs_accelerate/docker/proof-context/Dockerfile, external/ipfs_accelerate/scripts/proof_context/test_clean_install.py, external/ipfs_accelerate/test/proof_context/test_clean_install.py, artifacts/proof_carrying_context_engine/receipts/PCCE-054.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_clean_install.py && python external/ipfs_accelerate/scripts/proof_context/test_clean_install.py --artifacts artifacts/proof_carrying_context_engine/environment/artifact_hashes.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/clean-install
- Parallel lane: pcce-e-clean-install
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: external/ipfs_accelerate/.github/workflows/proof-context-clean-install.yml, external/ipfs_accelerate/docker/proof-context/Dockerfile, external/ipfs_accelerate/scripts/proof_context/test_clean_install.py, external/ipfs_accelerate/test/proof_context/test_clean_install.py, artifacts/proof_carrying_context_engine/receipts/PCCE-054.json
- Allowed paths: external/ipfs_accelerate/.github/workflows/proof-context-clean-install.yml, external/ipfs_accelerate/docker/proof-context/Dockerfile, external/ipfs_accelerate/scripts/proof_context/test_clean_install.py, external/ipfs_accelerate/test/proof_context/test_clean_install.py, artifacts/proof_carrying_context_engine/receipts/PCCE-054.json
- Conflict policy: CI and image consume frozen locks/artifacts only; they cannot repair packaging during validation.
- Acceptance: Clean installs and the optional container are reproducible from immutable artifacts without source-layout assumptions.

## PCCE-055 Create the synthetic example repository and walkthrough

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/examples/proof_context_repository, external/ipfs_accelerate/test/proof_context/test_example_repository.py, artifacts/proof_carrying_context_engine/receipts/PCCE-055.json
- Objective: Create a credential-free small Python Git fixture and executable walkthrough demonstrating initialization, scan, compression, local patch, incremental tests, proof reuse, expansion, bad-patch rejection, good-patch acceptance, and final seal.
- Depends on: PCCE-044
- Priority: P0
- Risk classification: medium-example-integrity
- Execution mode: supervised example implementation
- Allowed effects: Add the self-contained example directory, its test, and receipt; create disposable Git clones during validation.
- Prohibited effects: Embed real credentials/private data; depend on network or sibling layout; hard-code a passing fake seal; expose benchmark hidden answers; weaken bad-patch fixtures.
- Acceptance criteria: Fresh clone walkthrough is deterministic and documents every command/output identity; bad patch is rejected for a real governed reason; good patch passes incremental checks and seal; at least one proof is reused and context expansion is exercised.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_example_repository.py
- Required evidence: Fixture commit/tree; command transcript; before/after context tokens; selected tests; proof reuse; rejection/acceptance receipts; final seal CID.
- Rollback procedure: Revert the example directory/test and discard disposable clones; preserve validation receipts for diagnosis.
- Assigned worktree: pcce-PCCE-055
- Final result CID or artifact identity: pending example repository tree and walkthrough receipt identities
- Goal id: PCCE-G500
- Outputs: external/ipfs_accelerate/examples/proof_context_repository, external/ipfs_accelerate/test/proof_context/test_example_repository.py, artifacts/proof_carrying_context_engine/receipts/PCCE-055.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_example_repository.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/example
- Parallel lane: pcce-e-example
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/examples/proof_context_repository, external/ipfs_accelerate/test/proof_context/test_example_repository.py, artifacts/proof_carrying_context_engine/receipts/PCCE-055.json
- Allowed paths: external/ipfs_accelerate/examples/proof_context_repository, external/ipfs_accelerate/test/proof_context/test_example_repository.py, artifacts/proof_carrying_context_engine/receipts/PCCE-055.json
- Conflict policy: Example owns its complete isolated fixture directory; it may consume runtime packages but never become test/runtime authority.
- Acceptance: One small public fixture demonstrates the complete product behavior, including genuine rejection, expansion, reuse, acceptance, and sealing.

## PCCE-056 Seal installability and example acceptance gate

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: external/ipfs_accelerate/test/proof_context/test_installability_gate.py, artifacts/proof_carrying_context_engine/installation/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-056.json
- Objective: Qualify immutable package installation, supported profiles, reproducible environment evidence, optional container status, and the example workflow as the prerequisite for benchmark/security work.
- Depends on: PCCE-054, PCCE-055
- Priority: P0
- Risk classification: release-gate-critical
- Execution mode: supervised acceptance gate
- Allowed effects: Add the gate test; run read-only artifact/install/example validation; write qualification and receipt.
- Prohibited effects: Repair packaging/example code in the gate; use source imports; waive failed profiles; represent an unavailable required check as passed.
- Acceptance criteria: Dataset, kit, and accelerator artifacts and hashes verify; core/verification/Codex/evaluation and inventory-supported local profile resolve as declared; clean install and example pass; SBOM/manifest are complete; sibling/editable/mutable dependencies are absent; optional unsupported items are clearly limited.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_installability_gate.py external/ipfs_accelerate/test/proof_context/test_example_repository.py
- Required evidence: PCCE-050 through PCCE-055 receipts; artifact/lock/SBOM/environment CIDs; clean-install logs; example seal; explicit go or documented no-go.
- Rollback procedure: Publish failed qualification, invalidate benchmark/security release, and reopen only the owning predecessor; do not repair from gate worktree.
- Assigned worktree: pcce-PCCE-056
- Final result CID or artifact identity: pending CID for artifacts/proof_carrying_context_engine/installation/qualification.json
- Goal id: PCCE-G500
- Outputs: external/ipfs_accelerate/test/proof_context/test_installability_gate.py, artifacts/proof_carrying_context_engine/installation/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-056.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_installability_gate.py external/ipfs_accelerate/test/proof_context/test_example_repository.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/e/installability-gate
- Parallel lane: pcce-e-gate
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: external/ipfs_accelerate/test/proof_context/test_installability_gate.py, artifacts/proof_carrying_context_engine/installation/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-056.json
- Allowed paths: external/ipfs_accelerate/test/proof_context/test_installability_gate.py, artifacts/proof_carrying_context_engine/installation/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-056.json
- Conflict policy: Gate consumes immutable artifacts and unique evidence only; failure blocks both Epic F and Epic G.
- Acceptance: The v0.1 runtime is proven installable and demonstrable from immutable artifacts, or a precise no-go blocks qualification work.

## PCCE-060 Freeze benchmark schema, corpus manifest, configurations, and thresholds

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/specification.py, external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json, external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py, artifacts/proof_carrying_context_engine/benchmark/thresholds.json, artifacts/proof_carrying_context_engine/receipts/PCCE-060.json
- Objective: Define versioned task/corpus/result schemas, repository revision pins, hidden-answer isolation, configurations A–D, metrics, noninferiority margin, and qualification thresholds before any benchmark execution.
- Depends on: PCCE-056
- Priority: P0
- Risk classification: critical-evaluation-design
- Execution mode: supervised benchmark design
- Allowed effects: Add benchmark specifications/manifest/tests, preregister thresholds, and write receipt.
- Prohibited effects: Run evaluation before freeze; include future patches/answers in agent-visible context; tune thresholds after results; add a Hugging Face dataset; use mutable repository revisions.
- Acceptance criteria: Manifest requires at least typed structured, dynamic/plugin-heavy, and larger mature Python classes at exact commits; task kinds cover historical replay, controlled synthetic, assurance mutation, and negative human review; A–D are exact; all required context, quality, routing, verification, assurance, and economics metrics are typed; thresholds include 50–60% median context reduction, 30–50% total cost reduction, declared noninferiority, zero critical/stale/simulated acceptance, no controlled selected-test false negatives, and at most 20–25% routine frontier escalation.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py; python -m json.tool external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json; python -m json.tool artifacts/proof_carrying_context_engine/benchmark/thresholds.json
- Required evidence: Schema and manifest CIDs; threshold preregistration timestamp/identity; leakage model; exact revision reachability/availability probes; metric completeness matrix.
- Rollback procedure: Before execution, revert benchmark schema/manifest and issue a new freeze receipt; after execution starts, never edit in place—create a new corpus/version and invalidate comparisons.
- Assigned worktree: pcce-PCCE-060
- Final result CID or artifact identity: pending corpus-manifest and threshold CIDs
- Goal id: PCCE-G600
- Outputs: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/specification.py, external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json, external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py, artifacts/proof_carrying_context_engine/benchmark/thresholds.json, artifacts/proof_carrying_context_engine/receipts/PCCE-060.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py && python -m json.tool external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json && python -m json.tool artifacts/proof_carrying_context_engine/benchmark/thresholds.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/benchmark-freeze
- Parallel lane: pcce-f-specification
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/specification.py, external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json, external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py, artifacts/proof_carrying_context_engine/benchmark/thresholds.json, artifacts/proof_carrying_context_engine/receipts/PCCE-060.json
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/specification.py, external/ipfs_datasets/benchmarks/proof_context/corpus_manifest.json, external/ipfs_datasets/tests/proof_context/benchmarks/test_specification.py, artifacts/proof_carrying_context_engine/benchmark/thresholds.json, artifacts/proof_carrying_context_engine/receipts/PCCE-060.json
- Conflict policy: Frozen corpus, configurations, metric definitions, and thresholds are immutable once PCCE-061 or any benchmark run begins.
- Acceptance: Evaluation design is preregistered, versioned, pinned, leakage-resistant, and complete before observing results.

## PCCE-061 Build the typed structured Python corpus shard

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/benchmarks/proof_context/corpus/typed_structured, external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-061.json
- Objective: Materialize a frozen typed, well-structured Python repository shard with historical/synthetic tasks, assurance mutants, negative review tasks, hidden tests, and exact source/answer identities.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: high-benchmark-integrity
- Execution mode: supervised corpus construction
- Allowed effects: Add only the typed shard, its validator test, and receipt; fetch a pinned public source only under an explicit corpus-fetch permit.
- Prohibited effects: Expose hidden patches/tests to agent-visible files; use mutable refs; embed credentials/private data; rewrite expected outcomes after a run.
- Acceptance criteria: Shard resolves exact commit/tree and license; visible and hidden partitions are content-addressed and access-separated; task categories satisfy manifest; baseline patches/outcomes are frozen; mutations include omission/vacuity/context-expansion cases; negative tasks require human review.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py
- Required evidence: Source commit/tree/archive hash; visible/hidden manifest CIDs; license; task and expected-outcome CIDs; leakage/access audit.
- Rollback procedure: Remove the unadmitted shard and receipt; after any run, version a replacement shard and preserve the original identities/results.
- Assigned worktree: pcce-PCCE-061
- Final result CID or artifact identity: pending typed-structured shard CID and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_datasets/benchmarks/proof_context/corpus/typed_structured, external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-061.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/corpus-typed
- Parallel lane: pcce-f-corpus-typed
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/benchmarks/proof_context/corpus/typed_structured, external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-061.json
- Allowed paths: external/ipfs_datasets/benchmarks/proof_context/corpus/typed_structured, external/ipfs_datasets/tests/proof_context/benchmarks/test_typed_structured_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-061.json
- Conflict policy: This task exclusively owns one corpus shard; shared manifest/threshold bytes are read-only.
- Acceptance: A pinned, licensed, leak-resistant typed Python shard supplies all required task categories and hidden evaluation evidence.

## PCCE-062 Build the dynamic and plugin-heavy Python corpus shard

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/benchmarks/proof_context/corpus/dynamic_plugins, external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-062.json
- Objective: Materialize a frozen dynamic/plugin-heavy Python shard designed to exercise opaque fallbacks, context expansion, conservative impact, plugin discovery, negative review, and assurance behavior.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: high-benchmark-integrity
- Execution mode: supervised corpus construction
- Allowed effects: Add only the dynamic shard, validator test, and receipt; fetch pinned public source only with explicit permit.
- Prohibited effects: Force semantic completeness where code is opaque/dynamic; reveal hidden fixtures/answers; use mutable revisions; tailor outcomes after engine results.
- Acceptance criteria: Exact commit/tree/license and partitions verify; tasks include dynamic imports/plugin registration and expected conservative fallback; hidden tests detect missed plugins/out-of-scope edits; assurance/negative cases are frozen; agent-visible data excludes answers.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py
- Required evidence: Source and partition CIDs; license; opaque-fallback ground truth; hidden-test and mutation identities; leakage audit.
- Rollback procedure: Remove an unadmitted shard; after execution, publish only a new version while retaining original results and identities.
- Assigned worktree: pcce-PCCE-062
- Final result CID or artifact identity: pending dynamic-plugin shard CID and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_datasets/benchmarks/proof_context/corpus/dynamic_plugins, external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-062.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/corpus-dynamic
- Parallel lane: pcce-f-corpus-dynamic
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/benchmarks/proof_context/corpus/dynamic_plugins, external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-062.json
- Allowed paths: external/ipfs_datasets/benchmarks/proof_context/corpus/dynamic_plugins, external/ipfs_datasets/tests/proof_context/benchmarks/test_dynamic_plugins_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-062.json
- Conflict policy: This shard remains disjoint from typed/mature shards; opaque expected behavior cannot be weakened to improve scores.
- Acceptance: A pinned dynamic Python shard measures safe fallback, expansion, and plugin-sensitive quality without leakage.

## PCCE-063 Build the larger mature Python corpus shard

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/benchmarks/proof_context/corpus/mature_python, external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-063.json
- Objective: Materialize a frozen larger mature Python repository shard with realistic historical tasks, controlled tasks, assurance mutants, and human-review negatives at an exact upstream revision.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: high-benchmark-integrity
- Execution mode: supervised corpus construction
- Allowed effects: Add only the mature shard, validator test, and receipt; fetch the pinned public source with an explicit permit.
- Prohibited effects: Let agents access later upstream commits/PR patches; expose hidden answers; use network during task execution; repin after results; include incompatible licensing.
- Acceptance criteria: Source/archive/commit/tree/license verify; historical cutoff blocks future-patch access; hidden evaluation and expected outcomes are sealed separately; task mix is representative and bounded; full-test baseline passes at the pin.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py
- Required evidence: Upstream origin/commit/tree/archive hash; license; cutoff/leakage proof; baseline full-test receipt; task/answer partition CIDs.
- Rollback procedure: Remove an unadmitted shard; after any run, preserve it and create a new version rather than changing revisions or answers.
- Assigned worktree: pcce-PCCE-063
- Final result CID or artifact identity: pending mature-Python shard CID and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_datasets/benchmarks/proof_context/corpus/mature_python, external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-063.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/corpus-mature
- Parallel lane: pcce-f-corpus-mature
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/benchmarks/proof_context/corpus/mature_python, external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-063.json
- Allowed paths: external/ipfs_datasets/benchmarks/proof_context/corpus/mature_python, external/ipfs_datasets/tests/proof_context/benchmarks/test_mature_python_corpus.py, artifacts/proof_carrying_context_engine/receipts/PCCE-063.json
- Conflict policy: Exact historical cutoff and hidden partition are immutable; runner access is restricted to the declared visible projection.
- Acceptance: A realistically sized, pinned, leak-resistant mature Python shard supports credible external generalization measurement.

## PCCE-064 Implement benchmark configurations A and B

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_ab.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py, artifacts/proof_carrying_context_engine/receipts/PCCE-064.json
- Objective: Implement configuration A as frontier model plus ordinary retrieval and full verification, and B as the same frontier model plus semantic ContextPacks, with all other eligible controls held constant.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: high-experimental-validity
- Execution mode: supervised evaluation implementation
- Allowed effects: Add A/B runners and deterministic fake/replay tests; use bounded live provider calls only during PCCE-067 under its permit.
- Prohibited effects: Change model/revision/prompt policy between A/B except context method; expose hidden data; use incremental verification in A/B; count replay as live quality.
- Acceptance criteria: A records ordinary retrieval tokens and full verification; B records semantic pack/compression/fallback/expansion while retaining full verification; paired task/model/seed/environment identities match; unavailable live service remains unavailable.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py
- Required evidence: Configuration descriptors and CIDs; pairing invariants; replay determinism; hidden-data denial tests; full-verification trace.
- Rollback procedure: Revert A/B runner modules and invalidate any results with their configuration CIDs; corpus remains frozen.
- Assigned worktree: pcce-PCCE-064
- Final result CID or artifact identity: pending A/B configuration descriptor CIDs and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_ab.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py, artifacts/proof_carrying_context_engine/receipts/PCCE-064.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/config-ab
- Parallel lane: pcce-f-ab
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_ab.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py, artifacts/proof_carrying_context_engine/receipts/PCCE-064.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_ab.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py, artifacts/proof_carrying_context_engine/receipts/PCCE-064.json
- Conflict policy: Frozen spec owns configuration semantics; runner cannot adapt treatment after seeing outcomes.
- Acceptance: A/B form a controlled paired comparison of ordinary versus semantic context under the same frontier model and full verification.

## PCCE-065 Implement benchmark configurations C and D

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_cd.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py, artifacts/proof_carrying_context_engine/receipts/PCCE-065.json
- Objective: Implement C as semantic ContextPacks plus routing and incremental verification, and D as the complete governed runtime with sufficiency, expansion, assurance sampling, incremental seal, and human escalation.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: critical-evaluation-runtime
- Execution mode: supervised evaluation implementation
- Allowed effects: Add C/D runners and deterministic tests; bounded live calls occur only under PCCE-067 permit.
- Prohibited effects: Omit unavailable/failed cost; bypass governance in D; use hidden answers; reuse stale capsules/proofs; label replay live; silently fall back to frontier/full verification without recording escalation.
- Acceptance criteria: C records route and incremental verification/reuse; D enforces complete lifecycle and records sufficiency, expansions, assurance, sealing, and human review; all stages bind task/config/environment identities and expose actual route/escalation decisions.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py
- Required evidence: Configuration CIDs; lifecycle traces; stale/simulated negative tests; route/verification/assurance/seal measurement fixtures.
- Rollback procedure: Revert C/D runners and invalidate results bound to their CIDs; never rewrite frozen corpus or thresholds.
- Assigned worktree: pcce-PCCE-065
- Final result CID or artifact identity: pending C/D configuration descriptor CIDs and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_cd.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py, artifacts/proof_carrying_context_engine/receipts/PCCE-065.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/config-cd
- Parallel lane: pcce-f-cd
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_cd.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py, artifacts/proof_carrying_context_engine/receipts/PCCE-065.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/benchmarks/configurations_cd.py, external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py, artifacts/proof_carrying_context_engine/receipts/PCCE-065.json
- Conflict policy: C/D implement only frozen configuration semantics and cannot waive runtime policy or alter metric definitions.
- Acceptance: C and D measure progressively governed capability with every route, reuse, expansion, assurance, seal, and review decision visible.

## PCCE-066 Implement benchmark metric and qualification aggregation

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/metrics.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/comparison.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py, artifacts/proof_carrying_context_engine/receipts/PCCE-066.json
- Objective: Aggregate paired run artifacts into the complete context, quality, routing, verification, assurance, and economics metric set with explicit baselines, missingness, confidence, and noninferiority comparison.
- Depends on: PCCE-060
- Priority: P0
- Risk classification: critical-metric-integrity
- Execution mode: supervised evaluation implementation
- Allowed effects: Add pure metric/comparison modules, tests, and receipt.
- Prohibited effects: Impute unavailable results as pass/zero cost; call estimates observed; exclude failed-attempt costs; change preregistered denominators/thresholds; use hidden answers outside outcome scorer.
- Acceptance criteria: Metrics include all requested token/reduction/fallback, accepted/hidden/regression/scope/review/first-attempt, route/escalation, tests/proofs/cache/stale, mutants/critical/omission/vacuity/expansion, and inference/verification/proof/assurance/failure/human/total-cost measures; observed versus estimated and paired versus unpaired are explicit.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py
- Required evidence: Golden aggregation vectors; denominator/missingness tests; baseline labeling tests; noninferiority calculation; semantic outcome comparison trace.
- Rollback procedure: Revert metric modules and invalidate aggregate/qualification reports; preserve raw run artifacts unchanged.
- Assigned worktree: pcce-PCCE-066
- Final result CID or artifact identity: pending metric-set descriptor CID and task receipt
- Goal id: PCCE-G600
- Outputs: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/metrics.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/comparison.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py, artifacts/proof_carrying_context_engine/receipts/PCCE-066.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/metrics
- Parallel lane: pcce-f-metrics
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/metrics.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/comparison.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py, artifacts/proof_carrying_context_engine/receipts/PCCE-066.json
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/metrics.py, external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/comparison.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py, artifacts/proof_carrying_context_engine/receipts/PCCE-066.json
- Conflict policy: Pure aggregation consumes immutable raw results and preregistered definitions; raw results and thresholds are read-only.
- Acceptance: Every requested metric is reproducible from raw identity-bound observations with honest baselines, costs, missingness, and uncertainty.

## PCCE-067 Execute the frozen A–D benchmark corpus

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/benchmark/raw_results.jsonl, artifacts/proof_carrying_context_engine/benchmark/run_manifest.json, artifacts/proof_carrying_context_engine/benchmark/execution_receipt.json, artifacts/proof_carrying_context_engine/receipts/PCCE-067.json
- Objective: Execute every eligible frozen task through configurations A–D in isolated worktrees, preserve failed attempts, and record raw observations without changing corpus, configuration, metric, or threshold bytes.
- Depends on: PCCE-061, PCCE-062, PCCE-063, PCCE-064, PCCE-065, PCCE-066
- Priority: P0
- Risk classification: critical-cost-and-quality-evaluation
- Execution mode: supervised bounded evaluation
- Allowed effects: Create isolated benchmark worktrees; invoke explicitly permitted allowlisted providers; run bounded checks/proofs; write only raw results, run manifest, execution receipt, and task receipt.
- Prohibited effects: Access hidden future patches/answers from agent context; mutate corpus/configs/thresholds; reuse worktrees across arms; conceal failures/costs; accept simulation/replay as live; exceed provider/cost/network permits.
- Acceptance criteria: Each run binds corpus/task/config/model/revision/seed/environment/source tree; hidden evaluation occurs after patch proposal in a denied projection; A–D eligibility and missingness are explicit; all failures and costs are retained; zero stale/simulated evidence is accepted; unavailable live prerequisites produce documented external blocker/no-go, never synthetic results.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py; python -m json.tool artifacts/proof_carrying_context_engine/benchmark/run_manifest.json
- Required evidence: All precursor receipt CIDs; provider permits and model revisions; raw-result line CIDs; worktree/lease/fence/task receipts; cost ledger; hidden-access audit; complete attempt population.
- Rollback procedure: Cancel provider/process groups, fence publication, discard all benchmark worktrees, retain accrued costs and partial raw receipts, and restart only missing idempotency keys.
- Assigned worktree: pcce-PCCE-067
- Final result CID or artifact identity: pending raw-result population CID and benchmark execution receipt
- Goal id: PCCE-G600
- Outputs: artifacts/proof_carrying_context_engine/benchmark/raw_results.jsonl, artifacts/proof_carrying_context_engine/benchmark/run_manifest.json, artifacts/proof_carrying_context_engine/benchmark/execution_receipt.json, artifacts/proof_carrying_context_engine/receipts/PCCE-067.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_ab.py external/ipfs_accelerate/test/proof_context/benchmarks/test_configurations_cd.py external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py && python -m json.tool artifacts/proof_carrying_context_engine/benchmark/run_manifest.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/execute
- Parallel lane: pcce-f-execution
- Resource class: evaluation-large
- Implementation timeout seconds: 86400
- Predicted files: artifacts/proof_carrying_context_engine/benchmark/raw_results.jsonl, artifacts/proof_carrying_context_engine/benchmark/run_manifest.json, artifacts/proof_carrying_context_engine/benchmark/execution_receipt.json, artifacts/proof_carrying_context_engine/receipts/PCCE-067.json
- Allowed paths: artifacts/proof_carrying_context_engine/benchmark/raw_results.jsonl, artifacts/proof_carrying_context_engine/benchmark/run_manifest.json, artifacts/proof_carrying_context_engine/benchmark/execution_receipt.json, artifacts/proof_carrying_context_engine/receipts/PCCE-067.json
- Conflict policy: One fenced writer owns each run identity; corpus, hidden answers, configurations, thresholds, and raw terminal rows are immutable.
- Acceptance: The complete eligible frozen population has truthful raw A–D evidence, or a precise externally blocked/no-go population record explains what could not run.

## PCCE-068 Aggregate benchmark results and evaluate thresholds

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/benchmark/metrics.json, artifacts/proof_carrying_context_engine/benchmark/qualification.json, artifacts/proof_carrying_context_engine/benchmark/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-068.json
- Objective: Aggregate the frozen raw population, compare A–D, evaluate every preregistered threshold and noninferiority condition, and report actual results and limitations without upgrading missing evidence.
- Depends on: PCCE-067
- Priority: P0
- Risk classification: release-gate-critical
- Execution mode: supervised benchmark qualification
- Allowed effects: Read immutable raw results/thresholds; write metrics, qualification, human report, and receipt.
- Prohibited effects: Drop failed tasks; change denominators or thresholds; report estimates as observations; pass unavailable live evidence; claim causality beyond paired design; repair runtime/corpus.
- Acceptance criteria: Report includes every required metric, context and cost reduction, route distribution, proof reuse, assurance, confidence/missingness, per-repository-class results, threshold pass/fail, zero-tolerance violations, and explicit no-go where incomplete or below threshold.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py; python -m json.tool artifacts/proof_carrying_context_engine/benchmark/metrics.json; python -m json.tool artifacts/proof_carrying_context_engine/benchmark/qualification.json
- Required evidence: Raw population/execution CIDs; deterministic aggregate CID; threshold comparison table; failed/missing task ledger; independent recomputation result.
- Rollback procedure: Delete/revert only unmerged aggregate projections, fix the pure aggregator through a new task attempt, and preserve all raw evidence/thresholds unchanged.
- Assigned worktree: pcce-PCCE-068
- Final result CID or artifact identity: pending benchmark metrics and qualification CIDs
- Goal id: PCCE-G600
- Outputs: artifacts/proof_carrying_context_engine/benchmark/metrics.json, artifacts/proof_carrying_context_engine/benchmark/qualification.json, artifacts/proof_carrying_context_engine/benchmark/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-068.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_metrics.py && python -m json.tool artifacts/proof_carrying_context_engine/benchmark/metrics.json && python -m json.tool artifacts/proof_carrying_context_engine/benchmark/qualification.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/f/qualification
- Parallel lane: pcce-f-qualification
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: artifacts/proof_carrying_context_engine/benchmark/metrics.json, artifacts/proof_carrying_context_engine/benchmark/qualification.json, artifacts/proof_carrying_context_engine/benchmark/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-068.json
- Allowed paths: artifacts/proof_carrying_context_engine/benchmark/metrics.json, artifacts/proof_carrying_context_engine/benchmark/qualification.json, artifacts/proof_carrying_context_engine/benchmark/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-068.json
- Conflict policy: Aggregate outputs are projections over frozen evidence; a failed threshold remains failed and cannot be waived in this task.
- Acceptance: Benchmark evidence yields a complete, reproducible qualification result or an explicit no-go with every missed threshold and missing prerequisite visible.

## PCCE-070 Threat-model the v0.1 runtime and trust boundaries

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/docs/security/proof-context-v0.1-threat-model.md, external/ipfs_accelerate/test/proof_context/security/test_threat_model.py, artifacts/proof_carrying_context_engine/security/threat_model.json, artifacts/proof_carrying_context_engine/receipts/PCCE-070.json
- Objective: Produce a code-linked threat model for untrusted repositories/source prompt injection, malicious tests/fixtures, untrusted agents/patches, scope/process escape, evidence forgery/replay/poisoning, benchmark leakage, provider disclosure, concurrent mutation, interruption, and compromised adapters.
- Depends on: PCCE-056
- Priority: P0
- Risk classification: critical-security-design
- Execution mode: supervised threat analysis
- Allowed effects: Add threat-model document/validator test, machine-readable threat register, and receipt; inspect runtime code and tests read-only.
- Prohibited effects: Assume sandboxing from documentation; omit a required threat; disclose real secrets; repair implementation in this task; mark an untested control effective.
- Acceptance criteria: Each required threat has assets, actors, entry points, trust boundary, attack preconditions, impact, preventive/detective/recovery controls, code/test owner, residual risk, and task mapping; controls distinguish planned from observed and fail closed where evidence is unavailable.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_threat_model.py; python -m json.tool artifacts/proof_carrying_context_engine/security/threat_model.json
- Required evidence: Runtime/data-flow inventory; trust-boundary diagram source; threat-to-control-to-test matrix; residual-risk ledger; reviewer identity.
- Rollback procedure: Supersede with a versioned threat model before security execution; after tests begin, preserve the original model and issue an explicit delta.
- Assigned worktree: pcce-PCCE-070
- Final result CID or artifact identity: pending threat-model document/register CIDs
- Goal id: PCCE-G700
- Outputs: external/ipfs_accelerate/docs/security/proof-context-v0.1-threat-model.md, external/ipfs_accelerate/test/proof_context/security/test_threat_model.py, artifacts/proof_carrying_context_engine/security/threat_model.json, artifacts/proof_carrying_context_engine/receipts/PCCE-070.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_threat_model.py && python -m json.tool artifacts/proof_carrying_context_engine/security/threat_model.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/threat-model
- Parallel lane: pcce-g-threat-model
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/docs/security/proof-context-v0.1-threat-model.md, external/ipfs_accelerate/test/proof_context/security/test_threat_model.py, artifacts/proof_carrying_context_engine/security/threat_model.json, artifacts/proof_carrying_context_engine/receipts/PCCE-070.json
- Allowed paths: external/ipfs_accelerate/docs/security/proof-context-v0.1-threat-model.md, external/ipfs_accelerate/test/proof_context/security/test_threat_model.py, artifacts/proof_carrying_context_engine/security/threat_model.json, artifacts/proof_carrying_context_engine/receipts/PCCE-070.json
- Conflict policy: Threat register freezes before hardening tasks; newly found threats append a versioned finding and cannot be silently omitted.
- Acceptance: All specified adversaries and trust boundaries map to concrete existing or scheduled controls and executable acceptance tests.

## PCCE-071 Enforce worktree, process, network, secret, and path sandbox boundaries

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/sandbox.py, external/ipfs_accelerate/test/proof_context/security/test_sandbox.py, artifacts/proof_carrying_context_engine/receipts/PCCE-071.json
- Objective: Enforce disposable worktrees, protected-branch denial, network deny-by-default/provider allowlists, credential stripping, secret redaction, executable/path allowlists, resource/output/time bounds, cancellation, and process-tree cleanup.
- Depends on: PCCE-070
- Priority: P0
- Risk classification: critical-sandbox
- Execution mode: supervised security hardening
- Allowed effects: Add the runtime sandbox policy/adapter and hermetic adversarial tests; use only disposable process/worktree fixtures.
- Prohibited effects: Claim kernel/container isolation not actually provided; inherit production credentials; allow arbitrary network/filesystem/process targets; auto-mutate a protected branch; leave descendant processes.
- Acceptance criteria: Network is denied unless a route-scoped provider endpoint is allowlisted; secrets are absent/redacted; repository paths cannot escape the bound root/worktree; only argv allowlist executes; limits terminate descendants; malicious tests/fixtures cannot publish outside their sandbox; canonical branch remains unchanged.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_sandbox.py
- Required evidence: Denial traces for network/path/process/credentials; process-tree cleanup; worktree and protected-ref checks; resource-limit receipts; declared platform limitations.
- Rollback procedure: Cancel/fence executions, kill captured process groups, discard sandbox worktrees, revert the sandbox commit, and mark all results under the weakened boundary invalid.
- Assigned worktree: pcce-PCCE-071
- Final result CID or artifact identity: pending sandbox policy descriptor CID and task receipt
- Goal id: PCCE-G700
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/sandbox.py, external/ipfs_accelerate/test/proof_context/security/test_sandbox.py, artifacts/proof_carrying_context_engine/receipts/PCCE-071.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_sandbox.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/sandbox
- Parallel lane: pcce-g-sandbox
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/sandbox.py, external/ipfs_accelerate/test/proof_context/security/test_sandbox.py, artifacts/proof_carrying_context_engine/receipts/PCCE-071.json
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/proof_context/sandbox.py, external/ipfs_accelerate/test/proof_context/security/test_sandbox.py, artifacts/proof_carrying_context_engine/receipts/PCCE-071.json
- Conflict policy: Sandbox narrows existing supervisor permissions and cannot grant new authority; platform gaps are explicit no-go constraints.
- Acceptance: Untrusted source, tests, fixtures, and local agent commands execute only within bounded, credential-free, deny-by-default effects.

## PCCE-072 Harden receipt, proof-cache, and seal admission

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_kit_py
- Owned paths: external/ipfs_kit/ipfs_kit_py/proof_context/trust.py, external/ipfs_kit/tests/proof_context/test_trust_admission.py, artifacts/proof_carrying_context_engine/receipts/PCCE-072.json
- Objective: Add narrow kit admission checks for receipt forgery, stale proof replay, cache poisoning, simulated proof, invalid required signature, wrong environment/parent seal, and transitive CID corruption.
- Depends on: PCCE-070
- Priority: P0
- Risk classification: critical-evidence-integrity
- Execution mode: supervised security hardening
- Allowed effects: Add trust-admission wrapper/tests over canonical persistence and frozen contracts; write receipt.
- Prohibited effects: Implement another proof cache or signer; treat missing signature authority as valid; mutate stored immutable blocks; weaken canonical CID/freshness/parent checks.
- Acceptance criteria: Every admitted receipt/proof/seal verifies bytes/CID/schema/producer/repository/tree/environment/policy/generation/parents/signature-when-required and live provenance; stale, poisoned, simulated, invalid-signature, wrong-parent, corrupt, or unavailable evidence is rejected before reuse/publication.
- Required tests: python -m pytest -q external/ipfs_kit/tests/proof_context/test_trust_admission.py
- Required evidence: Positive/negative vector results; corruption/replay/poisoning matrix; signature-authority availability behavior; cache non-publication proof.
- Rollback procedure: Revert trust wrapper, invalidate all artifacts admitted through it, restore prior CAS root only via canonical recovery, and retain rejected/partial receipts.
- Assigned worktree: pcce-PCCE-072
- Final result CID or artifact identity: pending trust-admission descriptor CID and task receipt
- Goal id: PCCE-G700
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_context/trust.py, external/ipfs_kit/tests/proof_context/test_trust_admission.py, artifacts/proof_carrying_context_engine/receipts/PCCE-072.json
- Validation: python -m pytest -q external/ipfs_kit/tests/proof_context/test_trust_admission.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/evidence-trust
- Parallel lane: pcce-g-trust
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_kit/ipfs_kit_py/proof_context/trust.py, external/ipfs_kit/tests/proof_context/test_trust_admission.py, artifacts/proof_carrying_context_engine/receipts/PCCE-072.json
- Allowed paths: external/ipfs_kit/ipfs_kit_py/proof_context/trust.py, external/ipfs_kit/tests/proof_context/test_trust_admission.py, artifacts/proof_carrying_context_engine/receipts/PCCE-072.json
- Conflict policy: Wrapper delegates storage/proof semantics to canonical authorities and only narrows admission; identities cannot be repaired in place.
- Acceptance: Forged, stale, poisoned, simulated, corrupt, unsigned-required, or wrong-parent evidence cannot enter reuse or sealing.

## PCCE-073 Add patch, prompt-injection, command-injection, and policy adversarial tests

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py, external/ipfs_accelerate/test/proof_context/security/fixtures/patch_and_agent, artifacts/proof_carrying_context_engine/receipts/PCCE-073.json
- Objective: Prove end-to-end rejection of out-of-scope changes, deleted required tests, weakened proof obligations, source-comment prompt injection, shell/argument injection, model policy edits, compromised-adapter authority claims, and response scope lies.
- Depends on: PCCE-070
- Priority: P0
- Risk classification: critical-adversarial
- Execution mode: supervised adversarial testing
- Allowed effects: Add adversarial fixtures/tests and receipt; execute only in disposable sandboxed repositories with replay/fake agents.
- Prohibited effects: Change runtime code from this test task; weaken fixtures to pass; execute payloads against host/canonical branches; use live credentials; let the proposing adapter judge acceptance.
- Acceptance criteria: Each named attack reaches the intended boundary and is rejected with a typed status, bounded/redacted evidence, unchanged canonical branch/policy/required tests/proofs, and no escaped process/path/network effect; a valid nearby control patch still passes.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py
- Required evidence: One receipt per attack/control; before/after tree/policy/proof identities; sandbox denial traces; minimized counterexamples for any failure.
- Rollback procedure: Revert only fixtures/tests if malformed; any runtime failure is a no-go and must reopen the owning implementation task rather than altering the expected rejection.
- Assigned worktree: pcce-PCCE-073
- Final result CID or artifact identity: pending adversarial patch/agent test population CID and task receipt
- Goal id: PCCE-G700
- Outputs: external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py, external/ipfs_accelerate/test/proof_context/security/fixtures/patch_and_agent, artifacts/proof_carrying_context_engine/receipts/PCCE-073.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/adversarial-agent
- Parallel lane: pcce-g-adversarial-agent
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py, external/ipfs_accelerate/test/proof_context/security/fixtures/patch_and_agent, artifacts/proof_carrying_context_engine/receipts/PCCE-073.json
- Allowed paths: external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py, external/ipfs_accelerate/test/proof_context/security/fixtures/patch_and_agent, artifacts/proof_carrying_context_engine/receipts/PCCE-073.json
- Conflict policy: Expected security outcomes are immutable; a failing runtime control blocks qualification and cannot be papered over in fixture ownership.
- Acceptance: Untrusted repository and agent content cannot escape patch scope, remove checks, weaken proofs, inject commands, or rewrite governing policy.

## PCCE-074 Enforce hidden benchmark and provider-disclosure isolation

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_datasets_py
- Owned paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/isolation.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py, artifacts/proof_carrying_context_engine/receipts/PCCE-074.json
- Objective: Enforce separate visible/hidden benchmark projections, deny future patches/answers, minimize provider disclosure, and audit every context/provider payload against the frozen task access policy.
- Depends on: PCCE-070
- Priority: P0
- Risk classification: critical-evaluation-confidentiality
- Execution mode: supervised security hardening
- Allowed effects: Add benchmark access-control/projection logic, tests, and receipt; use synthetic denied fixtures only.
- Prohibited effects: Send hidden tests/answers/future patches to providers; allow arbitrary filesystem paths; log hidden bodies; infer access from filename only; weaken corpus seals.
- Acceptance criteria: Agent/provider context contains only declared visible CIDs; hidden scorer opens only after proposal closure in a separate denied projection; attempts to read hidden paths/future refs are rejected/audited; provider payload is bounded/redacted and policy-specific.
- Required tests: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py
- Required evidence: Visible/hidden access graphs; provider payload manifests; denial logs; future-ref tests; no-hidden-body logging proof.
- Rollback procedure: Revert isolation code, invalidate all benchmark results produced under it, and preserve the frozen corpus/hidden artifacts unchanged.
- Assigned worktree: pcce-PCCE-074
- Final result CID or artifact identity: pending benchmark-isolation descriptor CID and task receipt
- Goal id: PCCE-G700
- Outputs: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/isolation.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py, artifacts/proof_carrying_context_engine/receipts/PCCE-074.json
- Validation: python -m pytest -q external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/benchmark-isolation
- Parallel lane: pcce-g-benchmark-isolation
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/isolation.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py, artifacts/proof_carrying_context_engine/receipts/PCCE-074.json
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/proof_context/benchmarks/isolation.py, external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py, artifacts/proof_carrying_context_engine/receipts/PCCE-074.json
- Conflict policy: Hidden artifacts stay outside adapter/provider path ownership; scorer access is one-way and post-proposal.
- Acceptance: Agents and providers cannot observe hidden benchmark evidence, future answers, arbitrary host paths, or unnecessary repository data.

## PCCE-075 Add concurrent-writer and interrupted-execution adversarial integration tests

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py, external/ipfs_accelerate/test/proof_context/security/fixtures/concurrency, artifacts/proof_carrying_context_engine/receipts/PCCE-075.json
- Objective: Prove rejection and safe recovery for concurrent stale writers, lease/fence loss, duplicate adapter results, interrupted apply/check/proof/seal, and ambiguous terminal execution.
- Depends on: PCCE-071, PCCE-072, PCCE-073, PCCE-074
- Priority: P0
- Risk classification: critical-concurrency
- Execution mode: supervised adversarial integration
- Allowed effects: Add concurrency/crash fixtures/tests and receipt; create bounded processes and disposable worktrees/storage roots.
- Prohibited effects: Modify runtime/storage code from the test task; use shared canonical branches; leave live processes/worktrees; resolve ambiguity as success; hide race failures.
- Acceptance criteria: At most one fenced writer publishes from a generation; stale/ABA writers fail; duplicate terminal calls are idempotent; every injected crash converges to valid prior/new state or repair_required; ambiguous interruption never becomes accepted; cleanup leaves no process/worktree/storage leak.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py
- Required evidence: Race/crash schedule seeds; process/worktree/lease/CAS logs; parent-root/seal identities; cleanup audit; minimized failing schedule if any.
- Rollback procedure: Terminate process groups, fence writers, discard disposable state/worktrees, revert fixtures/tests if invalid, and reopen owning runtime/storage task on a real failure.
- Assigned worktree: pcce-PCCE-075
- Final result CID or artifact identity: pending concurrency adversarial population CID and task receipt
- Goal id: PCCE-G700
- Outputs: external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py, external/ipfs_accelerate/test/proof_context/security/fixtures/concurrency, artifacts/proof_carrying_context_engine/receipts/PCCE-075.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/adversarial-concurrency
- Parallel lane: pcce-g-adversarial-concurrency
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py, external/ipfs_accelerate/test/proof_context/security/fixtures/concurrency, artifacts/proof_carrying_context_engine/receipts/PCCE-075.json
- Allowed paths: external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py, external/ipfs_accelerate/test/proof_context/security/fixtures/concurrency, artifacts/proof_carrying_context_engine/receipts/PCCE-075.json
- Conflict policy: Security expectations remain fixed; race failures block release and return to the component owner with preserved schedule evidence.
- Acceptance: Concurrent mutation and ambiguous interruption cannot produce duplicate, stale, or falsely accepted evidence.

## PCCE-076 Audit and seal the v0.1 security gate

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/security/findings.json, artifacts/proof_carrying_context_engine/security/report.md, artifacts/proof_carrying_context_engine/security/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-076.json
- Objective: Reconcile the frozen threat model with observed sandbox, trust, adversarial, leakage, concurrency, and interruption evidence and produce severity-ranked findings plus explicit security qualification/no-go.
- Depends on: PCCE-075
- Priority: P0
- Risk classification: release-gate-critical
- Execution mode: supervised security acceptance gate
- Allowed effects: Read immutable security evidence; write findings, report, qualification, and receipt.
- Prohibited effects: Repair code/tests; downgrade severity without rationale; mark missing controls effective; waive a required adversarial test; expose secret/hidden fixture bodies.
- Acceptance criteria: Every threat has observed control/test disposition; all required adversarial cases pass or become explicit blockers; residual risks and platform sandbox limitations are stated; critical/high findings block the next qualification level according to policy; no unavailable check is passed.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_threat_model.py external/ipfs_accelerate/test/proof_context/security/test_sandbox.py external/ipfs_kit/tests/proof_context/test_trust_admission.py external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py; python -m json.tool artifacts/proof_carrying_context_engine/security/qualification.json
- Required evidence: PCCE-070 through PCCE-075 receipt CIDs; threat/control/test matrix; full logs; finding severity rationale; explicit go or documented no-go.
- Rollback procedure: Revert only report projections, preserve all observed evidence, and reopen the failing owner task; never alter threat/test outcomes in gate worktree.
- Assigned worktree: pcce-PCCE-076
- Final result CID or artifact identity: pending security findings/report/qualification CIDs
- Goal id: PCCE-G700
- Outputs: artifacts/proof_carrying_context_engine/security/findings.json, artifacts/proof_carrying_context_engine/security/report.md, artifacts/proof_carrying_context_engine/security/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-076.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/security/test_threat_model.py external/ipfs_accelerate/test/proof_context/security/test_sandbox.py external/ipfs_kit/tests/proof_context/test_trust_admission.py external/ipfs_accelerate/test/proof_context/security/test_adversarial_patch_and_agent.py external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py external/ipfs_accelerate/test/proof_context/security/test_adversarial_concurrency.py && python -m json.tool artifacts/proof_carrying_context_engine/security/qualification.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/g/security-gate
- Parallel lane: pcce-g-gate
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: artifacts/proof_carrying_context_engine/security/findings.json, artifacts/proof_carrying_context_engine/security/report.md, artifacts/proof_carrying_context_engine/security/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-076.json
- Allowed paths: artifacts/proof_carrying_context_engine/security/findings.json, artifacts/proof_carrying_context_engine/security/report.md, artifacts/proof_carrying_context_engine/security/qualification.json, artifacts/proof_carrying_context_engine/receipts/PCCE-076.json
- Conflict policy: Security gate is evidence-only; any material control failure blocks PCCE-080 and cannot be waived by this task.
- Acceptance: Security qualification is narrowly evidence-based, with every blocker and residual trust-boundary limitation explicit.

## PCCE-080 Add required current-head release CI

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: endomorphosis/ipfs_accelerate_py
- Owned paths: external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml, external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py, external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py, artifacts/proof_carrying_context_engine/ci/required_jobs.json, artifacts/proof_carrying_context_engine/receipts/PCCE-080.json
- Objective: Add fail-closed current-head CI jobs for clean install, imports, schema/vector parity, unit/integration/example/adversarial tests, benchmark smoke, receipt/seal verification, supported container build, and dependency/license scan.
- Depends on: PCCE-068, PCCE-076
- Priority: P0
- Risk classification: release-critical-ci
- Execution mode: supervised CI implementation
- Allowed effects: Add one required workflow, CI contract verifier/test, required-job manifest, and receipt; execute the workflow in an authorized CI context.
- Prohibited effects: Use continue-on-error, error-swallowing shell constructs, skipped required tests, mutable branch dependencies, source/editable installs, or unavailable checks represented as passed.
- Acceptance criteria: Every required job exists, consumes exact source/artifact/lock identities, fails on any command/check failure, uploads bounded receipts, and is required for current head; optional unsupported container is an explicit failing/limited qualification input rather than a pass.
- Required tests: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py; python external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py --workflow external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml
- Required evidence: Workflow digest; required-job manifest CID; successful current-head run/check URLs or connector identities; complete job logs; dependency/license findings; no-skip/error-swallow audit.
- Rollback procedure: Revert the workflow/verifier commit only after marking release blocked; preserve failed CI logs and never remove a required gate to obtain green status.
- Assigned worktree: pcce-PCCE-080
- Final result CID or artifact identity: pending required-job manifest CID and current-head CI run identity
- Goal id: PCCE-G800
- Outputs: external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml, external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py, external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py, artifacts/proof_carrying_context_engine/ci/required_jobs.json, artifacts/proof_carrying_context_engine/receipts/PCCE-080.json
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py && python external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py --workflow external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/h/current-head-ci
- Parallel lane: pcce-h-ci
- Resource class: ci-large
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml, external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py, external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py, artifacts/proof_carrying_context_engine/ci/required_jobs.json, artifacts/proof_carrying_context_engine/receipts/PCCE-080.json
- Allowed paths: external/ipfs_accelerate/.github/workflows/proof-context-v0.1.yml, external/ipfs_accelerate/scripts/proof_context/verify_release_ci.py, external/ipfs_accelerate/test/proof_context/test_release_ci_contract.py, artifacts/proof_carrying_context_engine/ci/required_jobs.json, artifacts/proof_carrying_context_engine/receipts/PCCE-080.json
- Conflict policy: Required gates may be strengthened but not bypassed; any unavailable required CI authority blocks release qualification.
- Acceptance: Current head has a complete, mandatory, immutable-input CI gate whose failures cannot be converted into green status.

## PCCE-081 Build the v0.1 release candidate bundle

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py, artifacts/proof_carrying_context_engine/release/v0.1-rc1, artifacts/proof_carrying_context_engine/receipts/PCCE-081.json
- Objective: Assemble a content-addressed v0.1 release candidate with exact commits, packages, locks, SBOM, environment, schemas/vectors, example, corpus/results, limitations, qualification status, rollback, release manifest, and seal-verification instructions.
- Depends on: PCCE-080
- Priority: P0
- Risk classification: critical-release-artifacts
- Execution mode: supervised release assembly
- Allowed effects: Add deterministic release builder; copy/link verified immutable inputs into the declared RC directory; write manifest, instructions, and receipt.
- Prohibited effects: Rebuild or repair inputs; omit failed/blocked evidence; alter artifacts after hashing; include credentials/hidden benchmark answers; publish externally or tag a release.
- Acceptance criteria: Manifest transitively binds exact source commits/trees, wheel/sdist hashes, dependency locks, SBOM, environment, all v0.1 schemas/vectors, example tree, visible corpus identity plus sealed hidden identity, benchmark/security/CI results, known limitations, rollback, and independent seal-verification commands; missing required input yields no-go.
- Required tests: python external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py --check artifacts/proof_carrying_context_engine/release/v0.1-rc1; python -m json.tool artifacts/proof_carrying_context_engine/release/v0.1-rc1/release_manifest.json
- Required evidence: All predecessor CIDs; deterministic two-build identity; manifest/transitive verification; package signature/hash results; no-secret/no-hidden-body scan.
- Rollback procedure: Withdraw the unpromoted RC directory/identity, retain its manifest and failure receipt, repair only through predecessor tasks, and build rc2 rather than overwrite rc1.
- Assigned worktree: pcce-PCCE-081
- Final result CID or artifact identity: pending release bundle CID and release_manifest.json identity
- Goal id: PCCE-G800
- Outputs: external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py, artifacts/proof_carrying_context_engine/release/v0.1-rc1, artifacts/proof_carrying_context_engine/receipts/PCCE-081.json
- Validation: python external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py --check artifacts/proof_carrying_context_engine/release/v0.1-rc1 && python -m json.tool artifacts/proof_carrying_context_engine/release/v0.1-rc1/release_manifest.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/h/release-candidate
- Parallel lane: pcce-h-rc
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py, artifacts/proof_carrying_context_engine/release/v0.1-rc1, artifacts/proof_carrying_context_engine/receipts/PCCE-081.json
- Allowed paths: external/ipfs_accelerate/scripts/proof_context/build_release_candidate.py, artifacts/proof_carrying_context_engine/release/v0.1-rc1, artifacts/proof_carrying_context_engine/receipts/PCCE-081.json
- Conflict policy: Release assembly is read-only over admitted inputs; rc1 is immutable once its manifest CID is emitted.
- Acceptance: One independently verifiable RC bundle contains every required source, package, contract, evaluation, security, limitation, and rollback artifact.

## PCCE-082 Assign the evidence-supported qualification level

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/qualification/level.json, artifacts/proof_carrying_context_engine/qualification/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-082.json
- Objective: Assign exactly one of research_demo, internal_alpha, internal_pilot, external_supervised_pilot, or production_candidate from installation, quality, security, benchmark, CI, and longitudinal self-hosting evidence.
- Depends on: PCCE-081
- Priority: P0
- Risk classification: critical-release-decision
- Execution mode: supervised qualification gate
- Allowed effects: Read immutable RC/evidence; write qualification level/report and receipt.
- Prohibited effects: Infer readiness from component completion; exceed internal_alpha without benchmark and longitudinal self-hosting passage; waive missing/security/zero-tolerance evidence; claim production readiness from board completion.
- Acceptance criteria: Default target is internal_alpha; internal_pilot requires frozen benchmark thresholds and longitudinal self-hosting checks; higher levels require their explicit policy evidence; every unmet next-level criterion and confidence/limitation is listed; no-go evidence can lower the level to research_demo.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/qualification/level.json; verify declared level against release manifest, benchmark qualification, security qualification, CI, and self-hosting receipts
- Required evidence: RC manifest CID; installation/benchmark/security/CI qualification CIDs; longitudinal self-hosting receipt or explicit unavailable blocker; deterministic policy decision trace.
- Rollback procedure: Supersede the qualification projection only when new immutable evidence exists; never relabel the same evidence to a higher level.
- Assigned worktree: pcce-PCCE-082
- Final result CID or artifact identity: pending qualification-level and report CIDs
- Goal id: PCCE-G800
- Outputs: artifacts/proof_carrying_context_engine/qualification/level.json, artifacts/proof_carrying_context_engine/qualification/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-082.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/qualification/level.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/h/qualification-level
- Parallel lane: pcce-h-qualification
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Predicted files: artifacts/proof_carrying_context_engine/qualification/level.json, artifacts/proof_carrying_context_engine/qualification/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-082.json
- Allowed paths: artifacts/proof_carrying_context_engine/qualification/level.json, artifacts/proof_carrying_context_engine/qualification/report.md, artifacts/proof_carrying_context_engine/receipts/PCCE-082.json
- Conflict policy: Qualification is a pure evidence-policy decision; missing or failed evidence can only hold or lower the level.
- Acceptance: The assigned level is the highest one fully supported by current immutable evidence, with all next-level blockers explicit.

## PCCE-083 Generate final task-board and go/no-go report

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Owning repository: cross-repository
- Owned paths: artifacts/proof_carrying_context_engine/final/supervisor_report.json, artifacts/proof_carrying_context_engine/final/supervisor_report.md, artifacts/proof_carrying_context_engine/final/dependency_graph.json, artifacts/proof_carrying_context_engine/receipts/PCCE-083.json
- Objective: Produce the final machine/human supervisor report, complete task/disposition graph, and explicit proceed, proceed-with-restrictions, or no-go recommendations for internal development, internal pilot, external supervised pilot, and production use.
- Depends on: PCCE-082
- Priority: P0
- Risk classification: critical-final-reporting
- Execution mode: supervised final evidence projection
- Allowed effects: Read immutable board/supervisor/task/release evidence; write final reports, dependency graph, and receipt.
- Prohibited effects: Change task status or evidence; omit failed/blocked/cancelled attempts; overstate production readiness; invent metrics; publish externally, merge autonomously, or waive blockers.
- Acceptance criteria: Reports include parent objective identity, final board, dependency graph, all dispositions, repositories/files changed, canonical ownership, public API, CLI/install examples, tests/CI, benchmark/context/cost/route/reuse/assurance/security results, release artifacts, qualification, every next-level blocker, and explicit recommendations; machine/human values agree.
- Required tests: python -m json.tool artifacts/proof_carrying_context_engine/final/supervisor_report.json; python -m json.tool artifacts/proof_carrying_context_engine/final/dependency_graph.json; verify every PCCE task and receipt identity is represented exactly once
- Required evidence: Board revision/CID; all terminal task receipts including failures/partial effects; RC/qualification CIDs; report cross-check; explicit unresolved blocker ledger.
- Rollback procedure: Supersede only the final projection after correcting source evidence through its owning task; preserve prior report identity and never rewrite task receipts.
- Assigned worktree: pcce-PCCE-083
- Final result CID or artifact identity: pending final supervisor report and dependency-graph CIDs
- Goal id: PCCE-G800
- Outputs: artifacts/proof_carrying_context_engine/final/supervisor_report.json, artifacts/proof_carrying_context_engine/final/supervisor_report.md, artifacts/proof_carrying_context_engine/final/dependency_graph.json, artifacts/proof_carrying_context_engine/receipts/PCCE-083.json
- Validation: python -m json.tool artifacts/proof_carrying_context_engine/final/supervisor_report.json && python -m json.tool artifacts/proof_carrying_context_engine/final/dependency_graph.json
- Board namespace: proof-carrying-context-engine-v0.1
- Bundle: pcce/h/final-report
- Parallel lane: pcce-h-final
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: artifacts/proof_carrying_context_engine/final/supervisor_report.json, artifacts/proof_carrying_context_engine/final/supervisor_report.md, artifacts/proof_carrying_context_engine/final/dependency_graph.json, artifacts/proof_carrying_context_engine/receipts/PCCE-083.json
- Allowed paths: artifacts/proof_carrying_context_engine/final/supervisor_report.json, artifacts/proof_carrying_context_engine/final/supervisor_report.md, artifacts/proof_carrying_context_engine/final/dependency_graph.json, artifacts/proof_carrying_context_engine/receipts/PCCE-083.json
- Conflict policy: Final report is an immutable projection of terminal evidence; recommendations cannot exceed PCCE-082 qualification or hide no-go gates.
- Acceptance: The report ends with this evidence-bounded claim: The completed semantic-compression, incremental verification, model-routing, assurance, and proof-sealing subsystems were integrated into one installable Proof-Carrying Context Engine. The engine was evaluated against the frozen task corpus and qualified only to the level supported by the current installation, quality, security, context-reduction, cost, and verification evidence.
