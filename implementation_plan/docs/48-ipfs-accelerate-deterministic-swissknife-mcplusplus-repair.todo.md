# Deterministic SwissKnife ↔ MCP++ Contract Repair Taskboard

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix `DCR-`.

Companion artifacts:

- architecture: `implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md`
- objective heap: `implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.objectives.md`
- scheduler: `config/deterministic_swissknife_mcplusplus_repair_scheduler.json`

Implementation authoring uses the ordered provider contract: Grok 4.5 primary,
then Codex GPT-5.6-Terra with high reasoning when the primary is locally
unavailable or unauthenticated, or reports typed quota exhaustion. The
resulting repair runtime is deterministic-only.
`abstain_review` and `defer_capability` are valid repair-runtime dispositions;
an LLM/provider repair fallback is not. Completion requires current external
validation and re-proof, never provider or task prose. In each task below,
`Runtime model calls: 0` is an acceptance condition for the built repair
runtime, while the context fields bound implementation-authoring workers.

## Parallel waves

```text
W0   DCR-000
W1   DCR-001 | DCR-002 | DCR-003 | DCR-004
W2   DCR-010 | DCR-011 | DCR-012 | DCR-013 | DCR-014
W3   DCR-020 | DCR-021 | DCR-022 | DCR-023 | DCR-024
W4   DCR-030 | DCR-031 | DCR-032 | DCR-033 | DCR-034 | DCR-035
W5   DCR-040 | DCR-041 | DCR-042 | DCR-043 | DCR-044 | DCR-045 | DCR-046 | DCR-047
W6   DCR-050 | DCR-051 | DCR-052 | DCR-053
W7   DCR-060 | DCR-061 | DCR-062 | DCR-063 | DCR-064
W8   DCR-070 | DCR-071 | DCR-072 | DCR-073 | DCR-074
W9   DCR-080 | DCR-081 | DCR-082 | DCR-083 | DCR-084
W10  DCR-090 | DCR-091 | DCR-092 | DCR-093 | DCR-094
W11  DCR-100 | DCR-101 | DCR-102 | DCR-103 | DCR-104
```

## DCR-000 Bootstrap and seal the deterministic repair control plane

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: control
- Depends on:
- Goal id: DCR-G000
- Outputs: implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.objectives.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.todo.md, config/deterministic_swissknife_mcplusplus_repair_scheduler.json, scripts/validate_deterministic_contract_repair_board.py, scripts/ops/agent_supervisor/implementation_supervisor_entry.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_repair_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_provider.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_ordered_provider_fallback.py
- Validation: python3 scripts/validate_deterministic_contract_repair_board.py --check-all; python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_provider.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_ordered_provider_fallback.py; python3 external/ipfs_accelerate/scripts/ops/agent_supervisor/configured_board_scheduler.py --repo-root . --config config/deterministic_swissknife_mcplusplus_repair_scheduler.json preflight
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/control
- Parallel lane: dcr-control
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Resource stage: analysis
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.objectives.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.todo.md, config/deterministic_swissknife_mcplusplus_repair_scheduler.json, scripts/validate_deterministic_contract_repair_board.py, scripts/ops/agent_supervisor/implementation_supervisor_entry.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_repair_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_provider.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_ordered_provider_fallback.py
- Predicted symbols: DCR-G000, DCR-000, validate_board, DeterministicRepairProvider
- Interfaces: DeterministicContractRepairPlan@1, DeterministicRepairProvider@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: scheduler-validation.json
- Conflict policy: Control artifacts become protected after validation; runtime refill cannot rewrite them.
- Preconditions: Repository roots and existing SCA/WPD artifacts are readable.
- Effects: Validated goal/task DAG, scheduler waves, safety floors, protected-path policy, and the minimal non-prompt deterministic executor route needed to self-host later tasks.
- Evidence subset: exact task and goal populations, dependency DAG, wave assignment, no-LLM invariants, generic scheduler preflight, deterministic provider tripwires
- Acceptance: Validator proves unique goals/tasks, complete references, acyclic dependencies, exact scheduler population, the exact ordered authoring-provider policy, zero-LLM repair-runtime metadata, and safe protected paths; the root implementation entry exists; all control files are tracked and checkout/gitlinks satisfy generic preflight; the resulting DeterministicRepairProvider invokes only the admitted repair state machine and cannot execute a prompt, shell-generated patch, model, or fallback.
- Embedding query: bootstrap deterministic contract repair control plane
- AST query: parse todo headings metadata dependencies and scheduler waves

## DCR-001 Seal the no-LLM execution and import policy

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authority
- Depends on: DCR-000
- Goal id: DCR-G010
- Outputs: config/deterministic_contract_repair_authority.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/no_llm_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_no_llm.py, external/ipfs_accelerate/test/api/test_agent_supervisor_no_llm_runtime_barrier.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_no_llm.py external/ipfs_accelerate/test/api/test_agent_supervisor_no_llm_runtime_barrier.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/authority
- Parallel lane: dcr-authority
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Resource stage: policy
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: config/deterministic_contract_repair_authority.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/no_llm_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_no_llm.py, external/ipfs_accelerate/test/api/test_agent_supervisor_no_llm_runtime_barrier.py
- Predicted symbols: NoLlmExecutionGuard, DeterministicRepairAuthorityPolicy
- Interfaces: DeterministicRepairAuthorityPolicy@1, NoLlmExecutionGuard@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/no-llm-policy.json
- Conflict policy: Strengthen existing authority policies; do not add a permissive fallback or alter unrelated provider profiles.
- Preconditions: DCR control plane validated.
- Effects: DCR startup and every transition reject model/provider imports, commands, routes, or nonzero counters.
- Evidence subset: import denylist, command denylist, route denial, zero counters, typed abstention
- Acceptance: Direct, indirect, retry, rescue, residual, and self-improvement model routes are rejected before invocation; missing deterministic capability returns typed defer/abstain.
- Embedding query: no LLM deterministic repair import route guard zero model calls
- AST query: llm provider residual invocation implementation provider rescue model imports

## DCR-002 Unify deterministic repair dispositions and authority records

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authority
- Depends on: DCR-000
- Goal id: DCR-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_contracts.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_contracts.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/authority
- Parallel lane: dcr-contracts
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Resource stage: analysis
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_contracts.py
- Predicted symbols: DeterministicRepairDisposition, RepairEvidenceEnvelope
- Interfaces: DeterministicRepairDisposition@1, RepairEvidenceEnvelope@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/disposition-schema.json
- Conflict policy: Align with ImplementationDisposition and RPR records; avoid a parallel completion authority.
- Preconditions: DCR-000 complete.
- Effects: Closed statuses for proved_valid, refuted_repairable, repaired_pending_validation, abstain_review, defer_capability, rejected, and completed.
- Evidence subset: exact roots, authority kind, counterexample, operator, validation, proof transition
- Acceptance: Unknown enum values and illegal authority transitions fail closed; observation or derivation cannot directly authorize mutation/completion.
- Embedding query: repair disposition authority evidence transition content identity
- AST query: ImplementationDisposition sca_rpr_admission contract repair receipts completion

## DCR-003 Define multi-root ownership, write scope, and pin policy

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authority
- Depends on: DCR-000
- Goal id: DCR-G010
- Outputs: config/deterministic_contract_repair_roots.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/root_ownership.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_root_ownership.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_root_ownership.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/authority
- Parallel lane: dcr-roots
- Resource class: cpu-small
- Implementation timeout seconds: 3600
- Resource stage: policy
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: config/deterministic_contract_repair_roots.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/root_ownership.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_root_ownership.py
- Predicted symbols: RepairRootOwnership, SubmodulePinAdmission
- Interfaces: RepairRootOwnership@1, SubmodulePinAdmission@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/root-policy.json
- Conflict policy: Never rewrite unknown dirty content; provider and consumer authorities remain distinct.
- Preconditions: Repository forest discovery available.
- Effects: Maps every contract, operator, output, commit, and root-pin update to exactly one owner tree.
- Evidence subset: root realpath, commit/tree, overlay digest, owner role, allowed writes, pin predecessor/successor
- Acceptance: Cross-root writes, unbound overlays, provider defects patched as consumer weakening, and premature pin updates are rejected.
- Embedding query: multi root ownership write scope submodule pin repair
- AST query: repository_forest worktrees root resolver submodule pin merge admission

## DCR-004 Publish deterministic capability and toolchain inventory

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authority
- Depends on: DCR-000
- Goal id: DCR-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/capabilities.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/deterministic_artifacts.py, data/agent_supervisor/deterministic_contract_repair/capabilities.json, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_capabilities.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_artifacts.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_capabilities.py external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_artifacts.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/authority
- Parallel lane: dcr-capabilities
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 3600
- Resource stage: proof
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/capabilities.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/deterministic_artifacts.py, data/agent_supervisor/deterministic_contract_repair/capabilities.json, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_capabilities.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_artifacts.py
- Predicted symbols: DeterministicRepairCapabilities, SolverReadiness, CapabilityEvidenceReceipt, materialize_deterministic_repair_artifacts, verify_deterministic_repair_artifacts
- Interfaces: DeterministicRepairCapabilities@1, SolverReadiness@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/capabilities.json
- Conflict policy: Probe only; do not install tools during authoritative execution or treat importability as conformance.
- Preconditions: Exact datasets checkout and optional prover executables are discoverable.
- Effects: Content-addressed module, executable, version, policy, self-test, reconstruction, and network-mode receipts.
- Evidence subset: Python origin, distribution version, executable digest/version, self-test, reconstruction, simulation/stub flags
- Acceptance: Stub, TODO, simulated, missing, wrong-version, or uninitialized capability is unavailable and cannot be selected.
- Embedding query: deterministic logic capability inventory toolchain self test reconstruction
- AST query: solver_readiness multi_prover_resources backend registry package capability probes

## DCR-010 Reconcile current WPD, SCA, RPR, Doctor, and Planner evidence

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: evidence
- Depends on: DCR-001, DCR-002, DCR-003, DCR-004
- Goal id: DCR-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_repair_current_state.py, data/agent_supervisor/deterministic_contract_repair/current-state.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_current_evidence.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_current_evidence.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/evidence
- Parallel lane: dcr-evidence
- Resource class: cpu-medium
- Implementation timeout seconds: 3600
- Resource stage: analysis
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_repair_current_state.py, data/agent_supervisor/deterministic_contract_repair/current-state.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_current_evidence.py
- Predicted symbols: CurrentImplementationEvidence, reconcile_current_evidence
- Interfaces: CurrentImplementationEvidence@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/current-state.json
- Conflict policy: Do not mark legacy tasks complete from file existence; run their validations and bind current bytes.
- Preconditions: Authority and capabilities sealed.
- Effects: Maps legacy goal/task evidence to present modules, tests, commits, gaps, and stale/missing receipts.
- Evidence subset: WPD 22-task status, SCA gates, RPR readiness, Doctor/Planner tests, live wiring call graph
- Acceptance: Every reused component is classified implemented_current, stale, incomplete, unwired, or conflicting; synthetic planner/Doctor evidence is explicitly reported.
- Embedding query: reconcile WPD SCA RPR Doctor Planner current tree evidence
- AST query: pre_implementation_provider_gate pre_implementation_kernel implementation_daemon existing tests boards

## DCR-011 Materialize one current multi-root forest and overlay identity

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: evidence
- Depends on: DCR-003, DCR-010
- Goal id: DCR-G020
- Outputs: data/agent_supervisor/deterministic_contract_repair/forest.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_forest.py; python3 -m external.ipfs_accelerate.ipfs_accelerate_py.agent_supervisor.analysis.deterministic_repair_forest validate --workspace . --artifact data/agent_supervisor/deterministic_contract_repair/forest.json
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/evidence
- Parallel lane: dcr-forest
- Resource class: io-medium
- Implementation timeout seconds: 3600
- Resource stage: indexing
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: data/agent_supervisor/deterministic_contract_repair/forest.json
- Predicted symbols: RepositoryForestManifest, DirtyOverlay
- Interfaces: RepositoryForestManifest@1, DirtyOverlay@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/forest.json
- Conflict policy: Record dirty state without modifying it; the reviewed module and test are sealed predecessor outputs and the artifact-carrier attempt changes only forest.json. A source/test defect abstains for a separate predecessor revision and reseal; nested or uninitialized roots remain explicit.
- Preconditions: Root policy and the prelanded forest module/test are validated at the pinned accelerator revision.
- Effects: Materializes only forest.json during task execution and binds root realpaths, commits, trees, recursive submodule pins, complete tracked/index/worktree/untracked/ignored overlays, reviewed exclusions, configuration, and the exact artifact-carrier/merge/todo-status lifecycle into one forest CID.
- Evidence subset: root IDs, head/tree, recursive gitlinks, overlay path/mode/blob/bytes/digest, ignored state, reviewed exclusions, config/policy root, carrier and completion-transition commits
- Acceptance: Relocation-stable portable identity and host-local projection agree; the checked-in receipt stays current only across the exact DCR-011 artifact-carrier, no-ff merge, and sole todo-to-completed transition; missing roots, changed overlays, unreviewed exclusions, extra transition paths, or later unrelated commits withhold downstream authority.
- Embedding query: current multi root forest dirty overlay identity
- AST query: repository_forest repository_forest_manifest snapshot submodule overlay

## DCR-012 Restore analyzer health and exact parser accounting

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: analyzer-health
- Depends on: DCR-011
- Goal id: DCR-G020
- Outputs: data/agent_supervisor/deterministic_contract_repair/analyzer-health.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_repair_analyzer_health.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_analyzer_health.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_analyzer_health.py; python3 -m external.ipfs_accelerate.ipfs_accelerate_py.agent_supervisor.analysis.deterministic_repair_analyzer_health validate --workspace . --forest data/agent_supervisor/deterministic_contract_repair/forest.json --artifact data/agent_supervisor/deterministic_contract_repair/analyzer-health.json --max-bytes 1048576
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/evidence
- Parallel lane: dcr-index
- Resource class: cpu-large
- Implementation timeout seconds: 7200
- Resource stage: indexing
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_repair_analyzer_health.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_analyzer_health.py, data/agent_supervisor/deterministic_contract_repair/analyzer-health.json
- Predicted symbols: AnalyzerHealth, RepositoryIndex
- Interfaces: AnalyzerHealth@1, RepositoryIndex@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/analyzer-health.json
- Conflict policy: Fix parsers or type explicit unsupported rows; never hide failures with exclusions, caps, threshold weakening, or a package-only scan. JSONC and oversized legitimate data/source files receive typed dispositions rather than false syntax errors. The analyzer must prove the DCR-011 forest at its exact reviewed completion commit, then bind only the strict DCR-012 carrier, no-ff integration, and todo-status transition; calling the DCR-011 live validator at an arbitrary later descendant is forbidden.
- Preconditions: The exact DCR-011 completion transition and forest bytes validate historically; the authority sandbox exposes only identity-checked read-only Git metadata for the reviewed linked worktree closure; and the digest-bound TypeScript 5.9.3 canary passes through the sealed `IPFS_ACCELERATE_TYPESCRIPT_JS`, package, version, Node, and image bindings.
- Effects: Enumerates all six RepairRootOwnership HEAD trees and emits a current whole-scope parse/index receipt with an exact failure funnel, a lossless deterministically compressed disposition ledger, and a safe-for-completion decision; TypeScript-family files are parsed through a bounded persistent worker rather than one Node process per file, and CAS/index intermediates remain private scratch rather than task outputs.
- Evidence subset: every tracked path disposition reconstructed from a versioned dictionary/prefix codec and deterministic compression, exact row count, uncompressed digest, per-root Merkle roots, DCR-011 historical completion proof, DCR-012 lifecycle commits, parser/compiler/runtime/image versions and digests, compiler canary, failures, reviewed unsupported classifications, exclusions, and thresholds
- Acceptance: The single canonical regular-file artifact stays below the supervisor file-admission limit while decoding to exactly one disposition for every forest path with no omissions or duplicates; its live CLI replay must pass at the exact merged target before completion and finish within the 900-second authority limit; legitimate source/data blobs up to the 32 MiB snapshot bound are inspected directly rather than rejected by the older 16 MiB provider limit; unavailable or digest-mismatched compiler evidence, active-source parse failures, unreviewed unsupported classifications, lifecycle drift, or missing Git-object authority cannot claim completion-safe analyzer health; the stored 22-failure stale baseline and a transient dirty-worktree projection cannot satisfy this task.
- Embedding query: analyzer health parser failures exact coverage current forest
- AST query: index_repository_contracts analyzer health parser registry coverage funnel

## DCR-013 Index complete actual provider registration and handler surfaces

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: actual-surfaces
- Depends on: DCR-011, DCR-012
- Goal id: DCR-G020
- Outputs: data/agent_supervisor/deterministic_contract_repair/provider-surfaces.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/provider_surface_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_provider_surface_health.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_provider_surface_health.py; python3 -m external.ipfs_accelerate.ipfs_accelerate_py.agent_supervisor.analysis.provider_surface_health validate --workspace . --forest data/agent_supervisor/deterministic_contract_repair/forest.json --artifact data/agent_supervisor/deterministic_contract_repair/provider-surfaces.json --max-bytes 1048576
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/evidence
- Parallel lane: dcr-surfaces
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Resource stage: extraction
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/provider_surface_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_provider_surface_health.py, data/agent_supervisor/deterministic_contract_repair/provider-surfaces.json
- Predicted symbols: PythonMcpSurfaceExtractor, ProviderSurfaceHealth
- Interfaces: PythonMcpSurfaceExtractor, ProviderSurfaceHealth@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/provider-surfaces.json
- Conflict policy: Expected descriptors cannot substitute for actual registrations; duplicate anchors remain ambiguous. The checked-in projection must replay at the exact merged target and may bind its predecessor through an explicit verified transition, never through transient worktree dirt.
- Preconditions: Healthy or explicitly bounded index exists.
- Effects: Exact accelerate, datasets, kit, and MCP++ registration/dispatcher/handler/effect surface inventory encoded as a compact dictionary/Merkle projection rather than the extractor's redundant raw source-file dump.
- Evidence subset: package root/tree identity, exact scanned-file count and inventory Merkle root, dictionary-coded path/symbol/registration/alias/schema/dispatcher/handler/effect rows, archive/test/generated classifications, unresolved and duplicate-equivalence rows
- Acceptance: All mandatory package roots are scanned and the canonical regular-file artifact stays below the supervisor file-admission limit without losing any active surface, blocker, or equivalence row; the live CLI decodes and replays it against the exact merged forest before completion; unresolved mandatory or duplicate-equivalence rows block parity; unchanged scan is deterministic.
- Embedding query: actual MCP provider registration dispatcher handler surface index
- AST query: PythonMcpSurfaceExtractor provider_surface_health package_mcp_interop tool registries

## DCR-014 Index SwissKnife desktop expected contracts and UI bindings

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: expected-contracts
- Depends on: DCR-011, DCR-012
- Goal id: DCR-G020
- Outputs: data/agent_supervisor/deterministic_contract_repair/desktop-expectations.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_desktop_expectations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_desktop_expectations.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_desktop_expectations.py; python3 -m external.ipfs_accelerate.ipfs_accelerate_py.agent_supervisor.analysis.deterministic_desktop_expectations validate --workspace . --forest data/agent_supervisor/deterministic_contract_repair/forest.json --artifact data/agent_supervisor/deterministic_contract_repair/desktop-expectations.json --max-bytes 1048576
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/evidence
- Parallel lane: dcr-desktop
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Resource stage: extraction
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/deterministic_desktop_expectations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_desktop_expectations.py, data/agent_supervisor/deterministic_contract_repair/desktop-expectations.json
- Predicted symbols: McpContractCatalog, UIIRDocument, MCPIDL, ORB
- Interfaces: McpContractCatalog@1, UIIRDocument, MCP-IDL, ORB
- Submodules: external/ipfs_accelerate, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/desktop-expectations.json
- Conflict policy: Preserve source authority precedence; inferred prose and archived tests cannot silently become reviewed requirements. The checked-in projection must replay at the exact merged target and may bind its predecessor through an explicit verified transition, never through transient worktree dirt.
- Preconditions: Current SwissKnife root indexed.
- Effects: Reuses the existing MCP contract catalog and SwissKnife extractor to catalog desktop clients, registries, descriptors, manifests, types, UI/UX IR, ORB/IDL, tests, and call sites with authority classes; large source inventories use compact dictionary/Merkle bindings.
- Evidence subset: source span, declaration kind, version, request/result/error, transport, UI action, authority and contradiction
- Acceptance: Every active desktop MCP consumer is accounted for in one canonical regular-file artifact under the supervisor admission limit; the live CLI decodes and replays it against the exact merged forest before completion; conflicts and obsolete/generated/archive sources are typed and do not override reviewed declarations.
- Embedding query: SwissKnife desktop expected MCP contracts UI ORB IDL catalog
- AST query: SwissKnife MCP client registry descriptors manifests desktop apps ORB IDL UI IR

## DCR-020 Canonicalize contract, schema, method, and CID identity

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: contract-catalog
- Depends on: DCR-013, DCR-014
- Goal id: DCR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_identity.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_identity.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/catalog
- Parallel lane: dcr-catalog
- Resource class: cpu-medium
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_identity.py
- Predicted symbols: CanonicalContractIdentity, canonical_json_cid, semantic_contract_key
- Interfaces: CanonicalContractIdentity@1, SemanticContractKey@1
- Submodules: external/ipfs_accelerate, Mcp-Plus-Plus, swissknife
- Generated artifacts: none
- Conflict policy: Preserve normative MCP++ canonicalization; never trust claimed CIDs without local recomputation.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Actual and expected inventories share one forest.
- Effects: One relocation-stable key for package, operation, direction, schema root, profile, transport, and runtime instance; all vectors remain inline or test-local because no standalone vector artifact is declared.
- Evidence subset: canonical bytes, local CID, claimed CID, semantic key, source roots
- Acceptance: Equivalent declarations converge; altered bytes, pseudo-CIDs, direction/profile changes, or duplicate aliases remain distinct and typed; no undeclared vector artifact is written.

## DCR-021 Build the complete cross-repository contract graph

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: contract-catalog
- Depends on: DCR-013, DCR-014, DCR-020
- Goal id: DCR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_graph.py, data/agent_supervisor/deterministic_contract_repair/mcp_contract_graph.json, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_graph.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_graph.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/catalog
- Parallel lane: dcr-graph
- Resource class: cpu-large
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_graph.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_graph.py
- Predicted symbols: McpContractGraph, ContractEdge, ContractAuthority
- Interfaces: McpContractGraph@1, ContractEdge@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/mcp_contract_graph.json
- Conflict policy: Unresolved edges and authority conflicts stay explicit; expected descriptors never masquerade as observed implementations.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Canonical identity and complete provider/desktop indexes exist.
- Effects: Links UI action through descriptor, ORB/IDL, MCP method/schema, mediator, route, dispatcher, handler, effect, receipt, and runtime identity.
- Evidence subset: nodes, typed edges, authority, spans, roots, unresolved and ambiguous paths
- Acceptance: Every mandatory consumer edge is resolved exactly once or is a typed blocker; graph CID reconstructs from canonical bytes.

## DCR-022 Bind launched MCP services to exact runtime identities

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-identity
- Depends on: DCR-011, DCR-020
- Goal id: DCR-G030
- Outputs: config/deterministic_contract_repair_services.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_service_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_runtime_service_identity.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_runtime_service_identity.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/catalog
- Parallel lane: dcr-runtime
- Resource class: io-medium
- Implementation timeout seconds: 7200
- Predicted files: config/deterministic_contract_repair_services.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_service_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_runtime_service_identity.py
- Predicted symbols: RuntimeServiceManifest, RuntimeServiceWitness
- Interfaces: RuntimeServiceManifest@1, RuntimeServiceWitness@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/runtime-witness.json
- Conflict policy: One reviewed endpoint per service role; endpoint availability without process/config identity is insufficient.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Forest and identity algorithms are sealed.
- Effects: Binds interpreter, module origins/digests, commits, arguments, environment allowlist, config/state CID, transport, endpoint, PID, and start time.
- Evidence subset: accelerate, datasets, kit process and endpoint identities
- Acceptance: Port disagreements are removed; process replacement, changed config/state, wrong checkout, or unbound endpoint invalidates observations.

## DCR-023 Observe initialize, list, call, logic, and profile behavior live

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: live-observation
- Depends on: DCR-021, DCR-022
- Goal id: DCR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_live_observer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_live_observer.py, data/agent_supervisor/deterministic_contract_repair/mcp-live-transcript.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_live_observer.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/catalog
- Parallel lane: dcr-live
- Resource class: network-local
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_live_observer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_live_observer.py
- Predicted symbols: McpLiveObserver, LiveContractTranscript
- Interfaces: McpLiveObservation@1, MCP JSON-RPC 2.0, MCP++ Profiles A-F
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/mcp-live-transcript.json
- Conflict policy: Local loopback only; do not mutate user data, infer missing calls, or convert transport errors into empty success.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Exact runtime witnesses and contract graph are current.
- Effects: Captures initialize, tools/list, one allowlisted safe tools/call, malformed/unknown calls, Profiles A-F probes, and datasets logic_tools/cec_prove.
- Evidence subset: raw request/response bytes, HTTP status, JSON-RPC ID/version, schemas, receipts, local CIDs, process witness
- Acceptance: All three services are observed; discovery/RPC failures are typed; process-local and datasets MCP logic results are canonically equivalent.

## DCR-024 Classify and deduplicate deterministic repair findings

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: mismatch
- Depends on: DCR-021, DCR-023
- Goal id: DCR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_mismatch.py, data/agent_supervisor/deterministic_contract_repair/mcp_contract_mismatch_findings.json, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_mismatch.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_mismatch.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/catalog
- Parallel lane: dcr-findings
- Resource class: cpu-medium
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_mismatch.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_mismatch.py
- Predicted symbols: ContractMismatch, MismatchClass, deduplicate_findings
- Interfaces: ContractMismatch@1, RepairFindingKey@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/mcp_contract_mismatch_findings.json
- Conflict policy: Preserve independent protocol, schema, authority, liveness, identity, mediation, and implementation defects even when names coincide.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Declared graph and live observations share one epoch.
- Effects: Deterministic earliest-broken-edge findings keyed by package, operation, direction, schema/profile/transport roots, and snapshot.
- Evidence subset: expected edge, observed edge, mismatch class, counterexample seed, canonical key
- Acceptance: Duplicate dag.put/get-style tasks collapse only when semantic keys match; expected-only, missing, ambiguous, and unobserved remain nonpassing.

## DCR-030 Normalize observed contracts into real datasets logic IR

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: logic-proof
- Depends on: DCR-024
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_integration.py, external/ipfs_accelerate/test/api/test_agent_supervisor_datasets_logic_ir_integration.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_datasets_logic_ir_integration.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-logic
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_integration.py, external/ipfs_accelerate/test/api/test_agent_supervisor_datasets_logic_ir_integration.py
- Predicted symbols: DatasetsLogicFacade, normalize_contract_evidence
- Interfaces: DatasetsLogicFacade@1, IRInputEnvelope@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/ir-input.json
- Conflict policy: Synthetic fixtures may test adapters but cannot establish production capability or proof authority.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Current graph, findings, source bytes, and datasets capability manifest exist.
- Effects: Injects observed AST, contract graph, KG, UI IR, SecurityIR, and deterministic vector evidence into the existing datasets provider registry.
- Evidence subset: input roots, adapter versions, module origins, family availability, normalization diagnostics
- Acceptance: No fixture-derived or bridge-only artifact substitutes for required production input; every normalized row binds original bytes and forest CID.

## DCR-031 Compile contract families and MCP++ profiles into obligations

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: logic-proof
- Depends on: DCR-030
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr031_mcp_contract_obligations.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr031_mcp_contract_obligations.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-obligations
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr031_mcp_contract_obligations.py
- Predicted symbols: McpContractObligationCompiler, ObligationFamily
- Interfaces: ContractObligation@1, ProfilesAThroughF@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, Mcp-Plus-Plus
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/mcp-contract-obligations.json
- Conflict policy: Compile reviewed semantics only; unsupported profile fragments remain explicit and cannot be weakened.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Real evidence is normalized.
- Effects: Emits baseline JSON-RPC, negotiation, Profiles A-F, registry/dispatch, runtime identity, mediation, and evidence-lifecycle properties.
- Evidence subset: premises, conclusions, logic fragment, required backend, source authority, expected counterexample
- Acceptance: Every mandatory edge has an obligation or typed unsupported reason; directionality, temporal authority, CID, schema, and effect semantics are preserved.

## DCR-032 Route obligations only to capability-qualified deterministic provers

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: logic-proof
- Depends on: DCR-004, DCR-031
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/multi_prover_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr032_multi_prover_router.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr032_multi_prover_router.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-prover
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/multi_prover_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr032_multi_prover_router.py
- Predicted symbols: MultiProverRouter, ProverCapabilityAdmission
- Interfaces: ProverPortfolio@1, SolverReadiness@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/prover-runs.json
- Conflict policy: Importability, simulated output, SAT without reconstruction, and unknown never count as proof.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Obligations and capability probes share policy/toolchain roots.
- Effects: Selects DCEC, TDFOL, SMT, theorem, or structural backends only where declared fragments and self-tests match.
- Evidence subset: backend selection, capability receipt, raw result, timing, deterministic seed, reconstruction input
- Acceptance: Required missing/unsupported/error backend fails closed; no general LLM or remote nondeterministic provider is representable.

## DCR-033 Reconstruct proofs and preserve minimal counterexamples

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: logic-proof
- Depends on: DCR-032
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/kernel_reconstruction.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr033_kernel_reconstruction.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr033_kernel_reconstruction.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-kernel
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/kernel_reconstruction.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr033_kernel_reconstruction.py
- Predicted symbols: reconstruct_proof, minimize_counterexample, ProofKernelReceipt
- Interfaces: ProofKernelReceipt@1, Counterexample@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/proof-kernel-reconstruction.json
- Conflict policy: Never fabricate proof children or copy an expected outcome into actual detector evidence.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Deterministic prover runs are available.
- Effects: Independently reconstructs accepted proofs and reduces refutations to replayable minimal contract counterexamples.
- Evidence subset: proof term/certificate, kernel version, reconstruction result, counterexample bytes, roots
- Acceptance: Unreconstructable proof becomes invalid; every refutation replays against the bound graph and live transcript without inferred observations.

## DCR-034 Cache proof evidence with exact invalidation dependencies

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: logic-proof
- Depends on: DCR-032, DCR-033
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/dcr_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_proof_cache.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_proof_cache.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-cache
- Resource class: io-medium
- Implementation timeout seconds: 3600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/dcr_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_proof_cache.py
- Predicted symbols: DcrProofCache, ProofDependencyRoot
- Interfaces: ProofCache@1, ProofInvalidation@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/cache-index.json
- Conflict policy: Cache only reconstructed evidence; any input, policy, solver, schema, source, runtime, or capability-root change invalidates it.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Proof and counterexample receipt schemas are sealed.
- Effects: Content-addressed proof lookup with complete reverse dependency invalidation.
- Evidence subset: cache key, dependency roots, receipt CID, hit/miss/invalidation reason
- Acceptance: Stale or cross-epoch evidence cannot be selected; cache-hit reconstruction equals a cold run.

## DCR-035 Enforce mandatory logic stages and fail closed on unknown

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: logic-proof
- Depends on: DCR-030, DCR-031, DCR-032, DCR-033, DCR-034
- Goal id: DCR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_logic_application.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/ir_logic_hooks.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ir_logic_required_fail_closed.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_ir_logic_required_fail_closed.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/logic
- Parallel lane: dcr-gate
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_logic_application.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/ir_logic_hooks.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ir_logic_required_fail_closed.py
- Predicted symbols: RequiredLogicStageGate, IR_APPLICATION_FAILED
- Interfaces: RequiredLogicStageGate@1, IRApplicationResult@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/logic-gate.json
- Conflict policy: Remove required-path exception swallowing, partial-stage pass, bridge-only availability, and default-true safety claims.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Logic family portfolio, reconstruction, and invalidation are implemented.
- Effects: Exact policy-required stage set is mandatory for diagnose, plan, admit, apply, and complete decisions.
- Evidence subset: required/ran/pass stage sets, unknown/unsupported/error rows, no-false-grant claim
- Acceptance: Empty surfaces, skipped stages, unsupported semantics, import failures, and UI bridge-only projections cannot pass or grant execution.

## DCR-040 Define the finite typed repair operator registry

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-035
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/registry.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operators.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operators.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-operators
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/registry.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operators.py
- Predicted symbols: OperatorDescriptor, OperatorRegistry, RepairOperatorRegistryError
- Interfaces: RepairOperator@1, RepairOperatorRegistry@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/repair-operators.json
- Conflict policy: Closed reviewed operators only; arbitrary prose, source bodies, shell fragments, and dynamically imported code are inadmissible.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Mandatory logic gate is fail closed.
- Effects: Each operator declares input schema, exact write scope, before/after predicates, preview, inverse, validations, and applicability proof.
- Evidence subset: operator ID/version/CID, schema, write set, preconditions, inverse, tests
- Acceptance: Unknown fields/operators and non-invertible or unbounded mutations are rejected before planning.

## DCR-041 Implement alias, registration, and unique-anchor operators

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/registry_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operator_repairs.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operator_repairs.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-registry-op
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/registry_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operator_repairs.py
- Predicted symbols: AddAliasOperator, BindRegistrationOperator, DisambiguateAnchorOperator
- Interfaces: RegistryRepairOperators@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/repair-operator-vectors.json
- Conflict policy: Never choose among multiple anchors by lexical score; ambiguity abstains unless a unique typed edge proves ownership.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Operator registry and canonical graph identities exist.
- Effects: Structural edits for missing aliases/registrations and provably duplicate anchors.
- Evidence subset: AST anchor, before hash, registry key, semantic target, inverse patch
- Acceptance: Mutation tests cover duplicates, wrong owners, stale spans, idempotence, and rollback; behavior postcondition replaces anchor-count-only validation.

## DCR-042 Implement fail-closed JSON-RPC, schema, CID, and profile operators

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-035, DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/protocol_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr042_protocol_repairs.py, swissknife/src/services/mcp/mcp-plus-plus-connector.ts, swissknife/test/mcp-plus-plus/connector-http.test.ts
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr042_protocol_repairs.py && cd swissknife && npm test -- --runInBand test/mcp-plus-plus/connector-http.test.ts
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-protocol-op
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/protocol_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr042_protocol_repairs.py, swissknife/src/services/mcp/mcp-plus-plus-connector.ts, swissknife/test/mcp-plus-plus/connector-http.test.ts
- Predicted symbols: JsonRpcValidationOperator, SchemaBindingOperator, CanonicalCidOperator, ProfileNegotiationOperator
- Interfaces: JSON-RPC 2.0, MCP++ Profiles A-F, ProtocolRepairOperators@1
- Submodules: external/ipfs_accelerate, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/protocol-repair-vectors.json
- Conflict policy: Never convert initialize/HTTP/RPC/policy errors to success, trust server verified flags, or downgrade an explicitly required profile.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Normative MCP++ obligations and counterexamples are available.
- Effects: Typed edits for status/version/ID/result-error/schema checks, local CID verification, capability subset negotiation, and fail-closed policy decisions.
- Evidence subset: malformed vectors, normative clause, source span/hash, postcondition proof
- Acceptance: Negative vectors cover HTTP errors, wrong IDs/version, bad schemas/CIDs/receipts, unsupported profiles, policy outage, and transport mismatch.

## DCR-043 Implement dispatcher, handler, and datasets logic-route operators

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/dispatch_repairs.py, external/ipfs_datasets/ipfs_datasets_py/mcp_server/tools_dispatch.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_dispatch_repairs.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_dispatch_repairs.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-dispatch-op
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/dispatch_repairs.py, external/ipfs_datasets/ipfs_datasets_py/mcp_server/tools_dispatch.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_dispatch_repairs.py
- Predicted symbols: BindDispatcherOperator, BindHandlerOperator, BindLogicToolOperator
- Interfaces: DispatchRepairOperators@1, tools_dispatch, logic_tools, cec_prove
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/dispatch-operator-vectors.json
- Conflict policy: Match exact signatures/effects; never create a handler body when semantics are absent or route logic to a model.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Provider surface and canonical operation graph identify a unique owner.
- Effects: Structural dispatcher/handler registration and datasets logic_tools exposure repairs.
- Evidence subset: registration/dispatcher/handler/effect chain, signature schema, local/MCP equivalence
- Acceptance: Same typed obligation reaches cec_prove locally and through live datasets MCP with equivalent canonical output/receipt identity.

## DCR-044 Implement transport, lifecycle, and browser mediation operators

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-022, DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/transport_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_transport_repairs.py, swissknife/web/js/core/mcp-plus-plus-desktop-client.js, swissknife/build-tools/configs/vite.web.config.ts, swissknife/test/mcp-plus-plus/browser-mediation.test.ts
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_transport_repairs.py && cd swissknife && npm test -- --runInBand test/mcp-plus-plus/browser-mediation.test.ts
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-transport-op
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/transport_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_transport_repairs.py, swissknife/web/js/core/mcp-plus-plus-desktop-client.js, swissknife/build-tools/configs/vite.web.config.ts, swissknife/test/mcp-plus-plus/browser-mediation.test.ts
- Predicted symbols: TransportBindingOperator, LifecycleBindingOperator, BrowserMediationOperator
- Interfaces: TransportRepairOperators@1, GovernedMcpMediator@1
- Submodules: external/ipfs_accelerate, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/transport-operator-vectors.json
- Conflict policy: Mutation must traverse one governed mediator; raw service proxies are read-only allowlisted or rejected.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Runtime service manifest and transport obligations exist.
- Effects: Repairs endpoint/health/lifecycle bindings, correlation/framing, and desktop same-origin mediation.
- Evidence subset: endpoint identity, route kind, method/effect class, middleware transcript, rollback
- Acceptance: Actual preview middleware tests prove no browser mutation bypass and no availability claim from health/initialize alone.

## DCR-045 Implement UI, ORB, IDL, mobile, and projection operators

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: repair-operators
- Depends on: DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/ui_projection_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr045_ui_projection_repairs.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr045_ui_projection_repairs.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-ui-op
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/ui_projection_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr045_ui_projection_repairs.py
- Predicted symbols: UiDescriptorOperator, OrbBindingOperator, IdlProjectionOperator
- Interfaces: UIProjectionRepairOperators@1, UIIRDocument, MCP-IDL, ORB
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/ui-projection-operator-vectors.json
- Conflict policy: Full ui_ux_ir and semantic roundtrip required; bridge-only, prose-inferred, or missing target projection abstains.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: UI/ORB/IDL graph edges and datasets UI logic capability are proved.
- Effects: Typed projection synchronization for desktop, web, CLI, mobile, ORB, and IDL artifacts.
- Evidence subset: source/target schema CIDs, semantic roundtrip, UI action, MCP binding, projection diff
- Acceptance: Every edited projection roundtrips to the same semantic IR and live action reaches the expected mediated MCP effect.

## DCR-046 Implement authorization, effect, and policy operators

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: repair-operators
- Depends on: DCR-031, DCR-040
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/security_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_security_operators.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_security_operators.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-security-op
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/security_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_security_operators.py
- Predicted symbols: AuthorizationBindingOperator, EffectAnnotationOperator, PolicyGateOperator
- Interfaces: SecurityRepairOperators@1, SecurityIR, MCP++ Profiles C-D
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/security-operator-vectors.json
- Conflict policy: Operators may restore reviewed bindings but cannot invent authority, policy semantics, UCAN grants, or effect classifications; those abstain for review.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Deontic/security obligations and exact effect graph are available.
- Effects: Repairs missing fail-closed enforcement and reviewed authority/effect linkage.
- Evidence subset: principal/audience, capability, revocation, obligations, temporal validity, execution-time check, effect
- Acceptance: Policy outage/missing decision denies; stale/revoked/wrong-audience grants fail; no server-supplied authorization assertion is trusted.

## DCR-047 Enforce codegen roundtrip and generated-source synchronization

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: repair-operators
- Depends on: DCR-041, DCR-042, DCR-043, DCR-044, DCR-045, DCR-046
- Goal id: DCR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/codegen_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_codegen_roundtrip.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_codegen_roundtrip.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/operators
- Parallel lane: dcr-codegen-op
- Resource class: cpu-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators/codegen_repairs.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_codegen_roundtrip.py
- Predicted symbols: RegenerateProjectionOperator, GoldenRoundtripValidator
- Interfaces: CodegenRepairOperators@1, GeneratedArtifactManifest@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/operator-vectors/codegen.json
- Conflict policy: Invoke only pinned deterministic generators; generated files must name their authority source and never overwrite hand-owned code.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: All operator families and ownership metadata are registered.
- Effects: Rebuilds derived schemas/types/descriptors and verifies source-to-generated-to-semantic roundtrip.
- Evidence subset: generator digest/args, authority source CID, output hashes, roundtrip result, inverse
- Acceptance: Two clean generations are byte-identical; stale generated artifacts fail validation and rollback restores the exact prior tree.

## DCR-050 Compose a production Doctor with current source and logic services

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: doctor
- Depends on: DCR-047
- Goal id: DCR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_doctor_runtime.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_composition.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_composition.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/doctor
- Parallel lane: dcr-doctor
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_doctor_runtime.py, external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_composition.py
- Predicted symbols: build_default_doctor_service, DeterministicDoctorService, DoctorCompositionRoot
- Interfaces: DeterministicDoctorService@1, DatasetsLogicFacade@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/doctor-capabilities.json
- Conflict policy: Exact checkout/worktree required; empty source bytes and deferred production stages are unavailable, not successful.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Operator registry and datasets logic gate are production-ready.
- Effects: One factory injects source reader, graph/finding store, logic facade, operator registry, proof cache, receipt store, and transaction controller.
- Evidence subset: component identities, checkout root, capability self-tests, source slice hashes, no-LLM guard
- Acceptance: Default factory has no empty/deferred mandatory backend and fails closed when exact checkout or required logic family is absent.

## DCR-051 Diagnose the earliest broken contract edge deterministically

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: doctor
- Depends on: DCR-024, DCR-050
- Goal id: DCR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_diagnosis.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_diagnosis.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/doctor
- Parallel lane: dcr-diagnosis
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_diagnosis.py
- Predicted symbols: diagnose_contract_failure, DoctorFinding
- Interfaces: DoctorFinding@1, DeterministicDoctorService@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/doctor-findings.json
- Conflict policy: Exact finding enums and graph order replace substring matching and lexical guesses.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Current typed mismatch and complete source slices are available.
- Effects: Finds the earliest failing edge and minimal supporting source/transcript/logic evidence.
- Evidence subset: finding enum, edge/key, counterexample, source bytes/hash/span, epoch CID
- Acceptance: Same inputs yield same diagnosis; ambiguity, stale bytes, and unsupported logic return typed abstain/defer and no transform.

## DCR-052 Select, prove, and bound Doctor transforms and impact

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: doctor
- Depends on: DCR-047, DCR-051
- Goal id: DCR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_doctor_synthesis.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_transform.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_transform.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/doctor
- Parallel lane: dcr-doctor-plan
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_doctor_synthesis.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_doctor_transform.py
- Predicted symbols: DoctorTransformProposal, synthesize_transform, prove_impact
- Interfaces: DoctorTransformProposal@1, RepairOperator@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/doctor-transforms.json
- Conflict policy: Doctor selects registered operators only and loses transform authority whenever logic, proof, source, or impact validation fails.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Unique diagnosis and applicable operator portfolio exist.
- Effects: Proposes exact operator/arguments/write set with applicability, noninterference, expected proof transition, and rollback evidence.
- Evidence subset: finding CID, operator CID, before/expected-after hashes, applicability proof, impact cone
- Acceptance: No prose source body is produced; unmodeled effects, cross-root semantic changes, or proof failure abstain for review.

## DCR-053 Terminate Doctor at a proved fixed point or typed abstention

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: doctor
- Depends on: DCR-035, DCR-052
- Goal id: DCR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_doctor_runtime.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_doctor_fixed_point.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_doctor_fixed_point.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/doctor
- Parallel lane: dcr-doctor-fixed
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/deterministic_doctor_runtime.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_doctor_fixed_point.py
- Predicted symbols: DoctorFixedPoint, NoProgressGuard
- Interfaces: DoctorFixedPoint@1, DeterministicRepairDisposition@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/doctor-fixed-point.json
- Conflict policy: Repeated identical findings/proposals never trigger free retry, weaker gate, or model fallback.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Diagnosis and transform synthesis receipts are content addressed.
- Effects: Detects cycles/no progress and returns proved_valid, refuted_repairable, abstain_review, or defer_capability.
- Evidence subset: state hashes, transition measure, repeated keys, disposition, receipt roots
- Acceptance: Doctor terminates within the configured bound; no-progress yields one stable typed disposition and zero model/provider calls.

## DCR-060 Compose the production Planner with Doctor and datasets logic

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: planner
- Depends on: DCR-053
- Goal id: DCR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_planner_factory.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_planner_factory.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/planner
- Parallel lane: dcr-planner
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_planner_factory.py
- Predicted symbols: build_default_planner_handles, PlannerCompositionRoot
- Interfaces: DefaultPlannerHandles@1, DatasetsLogicFacade@1, DeterministicDoctorService@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/planner-capabilities.json
- Conflict policy: Required planner IR hooks propagate typed failures; exception swallowing and synthetic capability probes are forbidden.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Production Doctor and logic facade are available.
- Effects: One factory injects compiler, validator, replanner, candidate portfolio, scheduler, Doctor, logic, proof, and receipt services.
- Evidence subset: component identities, capability receipts, policy roots, self-tests
- Acceptance: Default handles exercise real services; missing mandatory component is unavailable and cannot mint planner-view evidence.

## DCR-061 Compile Doctor transforms into ownership-safe task DAGs

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: planner
- Depends on: DCR-003, DCR-060
- Goal id: DCR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_validator.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/proof_carrying_repair_dag.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_plan_dag.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_plan_dag.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/planner
- Parallel lane: dcr-plan-dag
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_validator.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/proof_carrying_repair_dag.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_plan_dag.py
- Predicted symbols: FormalPlanCompiler, FormalPlanValidator, RepairPlanNode, ProofCarryingRepairPlan, compile_proof_carrying_repair_plan
- Interfaces: ProofCarryingRepairPlan@1, RepairPlanNode@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/plan-dag-fixtures.json
- Conflict policy: Each node has one owner root and exact write set; provider/consumer semantics and submodule pin updates retain explicit order.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Admitted Doctor transform and root ownership policy exist.
- Effects: Compiles operator, evidence, proof, validation, rollback, resource, and dependency bindings into an acyclic DAG.
- Evidence subset: node CIDs, dependencies, owner, write set, before hash, validation, rollback, proof transition
- Acceptance: Missing bindings, cycles, cross-root writes, premature pin updates, prose nodes, or provider/model nodes are structurally unrepresentable.

## DCR-062 Generate and admit a finite symbolic candidate portfolio

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: planner
- Depends on: DCR-035, DCR-061
- Goal id: DCR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/symbolic_candidate_planner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_candidate_portfolio.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_admission.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_portfolio.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_admission.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_portfolio.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/planner
- Parallel lane: dcr-candidates
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/symbolic_candidate_planner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_candidate_portfolio.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_admission.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_candidate_portfolio.py
- Predicted symbols: SymbolicCandidatePlanner, CandidateAdmission, CandidateFacts, CandidatePortfolio, build_deterministic_candidate_portfolio
- Interfaces: RepairCandidate@1, CandidateAdmission@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/candidate-portfolios.json
- Conflict policy: Enumerate registered operators and bounded arguments only; no natural-language implementation candidate or silent IR attachment failure.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Valid formal plan schema and fail-closed logic gate exist.
- Effects: Ranks finite candidates by proved applicability, risk, edit size, resource cost, and validation strength.
- Evidence subset: candidate CID, operator args, score terms, proof receipt, rejected reason
- Acceptance: Selected candidate is uniquely admitted; ties/unknowns abstain, and all candidates bind current evidence and exact operator CIDs.

## DCR-063 Add typed failure memory and non-thrashing replanning

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: planner
- Depends on: DCR-062
- Goal id: DCR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_replanner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/adaptive_planner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_failure_memory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_replan_memory.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_replan_memory.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/planner
- Parallel lane: dcr-replan
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_replanner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/adaptive_planner.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/deterministic_failure_memory.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_replan_memory.py
- Predicted symbols: FormalReplanner, FailureMemory, RetryMeasure, FailureAttempt, FailureMemoryReceipt, decide_replan
- Interfaces: FailureMemory@1, ReplanDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/replan-fixtures.json
- Conflict policy: Retry only on typed new evidence or a strictly decreasing measure; never erase counterexamples or relax policy.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Candidate admission emits complete rejection/failure reasons.
- Effects: Persists stale, conflict, validation, proof, resource, and capability failures across restart.
- Evidence subset: attempt key, failure class, prior candidate, new evidence, measure, disposition
- Acceptance: Replaying unchanged inputs emits no duplicate work; retry/rescue cannot route to a provider/model or repeat a refuted candidate.

## DCR-064 Schedule plans within leases, lanes, and resource budgets

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: planner
- Depends on: DCR-061, DCR-063
- Goal id: DCR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/repair_resource_scheduler.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_resource_scheduler.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_resource_scheduler.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/planner
- Parallel lane: dcr-schedule
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/repair_resource_scheduler.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_resource_scheduler.py
- Predicted symbols: RepairResourceScheduler, PathLeasePlan
- Interfaces: RepairResourceSchedule@1, PathLease@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/resource-schedules.json
- Conflict policy: Serialize overlapping paths, roots, endpoints, and solver resources; strict sharding cannot override dependencies.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Acyclic plan and persisted failure memory exist.
- Effects: Assigns lanes, leases, fencing tokens, timeouts, retry budgets, and validation resources deterministically.
- Evidence subset: schedule CID, lane/shard, conflict graph, lease/fence, budgets, critical path
- Acceptance: Same plan/policy yields same schedule; overlapping writes never execute concurrently and starvation/deadlock tests terminate.

## DCR-070 Admit exact proof-carrying repair packets

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: execution
- Depends on: DCR-064
- Goal id: DCR-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_rpr_admission.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_repair_admission.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_repair_admission.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/execution
- Parallel lane: dcr-admission
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_rpr_admission.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_repair_admission.py
- Predicted symbols: RepairPacketAdmission, ProofCarryingRepairPacket
- Interfaces: RPR@1, ProofCarryingRepairPacket@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/admission-vectors.json
- Conflict policy: Require stored resolvable receipts; synthetic CIDs, booleans, prose, missing plan admission, and stale roots cannot authorize mutation.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Planner emits a validated resource schedule and admitted candidate.
- Effects: Freezes epoch, finding, Doctor, Planner, operator, source spans/hashes, proof, impact, validations, inverse, owner, and lease bindings.
- Evidence subset: packet CID, all referenced receipt CIDs, canonical reconstruction, authority transition
- Acceptance: Any missing/mismatched/unresolvable binding rejects before worktree creation; only derived plus admitted evidence grants execution.

## DCR-071 Replace catalog materialization with structural source edits

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: execution
- Depends on: DCR-047, DCR-070
- Goal id: DCR-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/materialize.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/edit_plan.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/engine.py, external/ipfs_accelerate/test/api/test_agent_supervisor_autonomous_repair_source_edit_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_source_materializer.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_autonomous_repair_source_edit_gate.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_source_materializer.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/execution
- Parallel lane: dcr-materialize
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/materialize.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/edit_plan.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/engine.py, external/ipfs_accelerate/test/api/test_agent_supervisor_autonomous_repair_source_edit_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_source_materializer.py
- Predicted symbols: StructuralRepairMaterializer, CodeEditPacket, AdmittedSourceEditOperator, apply_operator
- Interfaces: StructuralRepairMaterializer@1, CodeEditPacket@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/materialization-vectors.json
- Conflict policy: Resolve every path beneath the admitted owner worktree; write only operator-rendered edits with exact old-span hash and unique AST anchor.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Repair packet admission and operator registry are valid.
- Effects: Previews and applies real source/structured-data mutations; catalog bindings remain evidence, never mutation success.
- Evidence subset: before/after bytes and hashes, AST anchor, operator args, patch/inverse, write receipt
- Acceptance: A successful result contains changed source bytes and reversible diff; analysis-only/missing/IDL rows and receipt-write failures are nonpassing.

## DCR-072 Execute isolated multi-root transactions with rollback

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: execution
- Depends on: DCR-003, DCR-071
- Goal id: DCR-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/transaction.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/engine.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_transaction.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_transaction.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/execution
- Parallel lane: dcr-transaction
- Resource class: io-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/transaction.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/engine.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_transaction.py
- Predicted symbols: MultiRootRepairTransaction, RollbackJournal, FencedWrite
- Interfaces: MultiRootRepairTransaction@1, RollbackJournal@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/transaction-receipts.json
- Conflict policy: Never touch the user checkout; bind dirty overlays, use isolated owner worktrees, path leases/fences, and explicit cross-root commit order.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Structural materializer and resource schedule are admitted.
- Effects: Applies all nodes atomically per owner and rolls back every write/derived artifact/process on failure or cancellation.
- Evidence subset: worktree/root IDs, leases/fences, journal, diffs, process changes, rollback verification
- Acceptance: Stale, dirty-unbound, out-of-scope, symlink-escape, lease-race, partial-write, crash, and cancellation tests leave no promoted mutation.

## DCR-073 Validate, reindex, observe, and re-prove the new epoch

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: execution
- Depends on: DCR-035, DCR-072
- Goal id: DCR-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/validation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_post_repair_validation.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_post_repair_validation.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/execution
- Parallel lane: dcr-validation
- Resource class: cpu-large
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/validation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_post_repair_validation.py
- Predicted symbols: PostRepairValidator, RepairProofTransition
- Interfaces: PostRepairValidation@1, RepairProofTransition@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/post-repair-epoch.json
- Conflict policy: Expected results never substitute for detector output; unsupported/skipped mandatory checks and synthetic release children fail.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Transaction contains actual source edits.
- Effects: Runs format/type/unit/negative tests, starts exact services, reobserves live contracts, reindexes, recompiles, and reconstructs the post-edit proof.
- Evidence subset: commands/results, changed forest/runtime roots, transcripts, graph diff, proof transition, model-call counters
- Acceptance: Finding disappears for the intended semantic reason, no protected invariant regresses, all mandatory gates run, and zero model/provider calls are observed.

## DCR-074 Emit merge, commit, submodule-pin, and provenance evidence

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: execution
- Depends on: DCR-073
- Goal id: DCR-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/publish.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_merge_provenance.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_merge_provenance.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/execution
- Parallel lane: dcr-publish
- Resource class: io-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/publish.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_merge_provenance.py
- Predicted symbols: RepairPublisher, MergeProvenance, SubmodulePinTransition
- Interfaces: RepairPublication@1, MergeProvenance@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/publication.json
- Conflict policy: Provider commits precede consumer/pin commits; merges require current validation and never overwrite unrelated user changes.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: New epoch is fully validated and re-proved.
- Effects: Produces ordered commit/merge proposal, pin predecessor/successor, provenance DAG, release receipt, and authoritative publication event.
- Evidence subset: commits/trees, parentage, diffs, validation/proof CIDs, pins, merge decisions
- Acceptance: Every published byte traces to an admitted operator; conflicts or changed target head return stale/replan, never implicit merge success.

## DCR-080 Wire real Planner, Doctor, logic, and repair services into the live daemon

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: supervisor
- Depends on: DCR-050, DCR-060, DCR-074
- Goal id: DCR-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/deterministic_repair_composition.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_provider_gate.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_daemon_composition.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py external/ipfs_accelerate/test/api/test_agent_supervisor_no_legacy_residual.py external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_daemon_composition.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/supervisor
- Parallel lane: dcr-daemon
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/deterministic_repair_composition.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_provider_gate.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_daemon_planner_doctor_hook.py, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_daemon_composition.py
- Predicted symbols: build_repair_composition_root, DeterministicRepairCompositionRoot, evaluate_pre_implementation_gate, run_deterministic_repair
- Interfaces: DeterministicRepairCompositionRoot@1, PreImplementationKernel@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/daemon-composition.json
- Conflict policy: Remove allow_legacy_residual, synthetic planner/Doctor/obligation CIDs, availability booleans, and successful empty CompletedProcess behavior.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Planner, Doctor, transaction, validation, and publisher are production-ready.
- Effects: Live worker calls real services and persists DISCOVER→DIAGNOSE→PLAN→PROVE→SYNTHESIZE→APPLY→VALIDATE→REINDEX→REPROVE→PUBLISH.
- Evidence subset: resolvable service receipts per transition, source mutations, validations, state journal, no-LLM counters
- Acceptance: A deterministic close always has a repair/publication receipt or proved-valid observation; missing service receipt abstains and no path authorizes an LLM.

## DCR-081 Make selection and refill consume typed repair dispositions

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: supervisor
- Depends on: DCR-080
- Goal id: DCR-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/objective_graph.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/deterministic_repair_selection.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_selection_refill.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_selection_refill.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/supervisor
- Parallel lane: dcr-selection
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/objective_graph.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/deterministic_repair_selection.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_selection_refill.py
- Predicted symbols: select_deterministic_repair_task, project_repair_disposition, RepairSelectionEvidence, RepairSelectionResult, select_and_refill_repairs
- Interfaces: RepairTaskSelection@1, DeterministicRepairDisposition@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/selection-fixtures.json
- Conflict policy: Evidence state drives selection; task prose, file existence, missing/analysis-only rows, and skipped gates cannot imply completion.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Live daemon persists typed transitions.
- Effects: Selects ready findings/tasks by dependency, authority, risk, ownership, capability, and failure memory; deterministic refill deduplicates canonical keys.
- Evidence subset: candidate population, exclusion reason, chosen task, dependency closure, refill provenance
- Acceptance: No completed/blocked/review/unsupported/stale item executes; unchanged fixed-point state creates no new tasks.

## DCR-082 Make retry, rescue, restart, and recovery deterministic-only

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: supervisor
- Depends on: DCR-063, DCR-080
- Goal id: DCR-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/failure_replan_policy.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/deterministic_repair_recovery.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_recovery.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_recovery.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/supervisor
- Parallel lane: dcr-recovery
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/failure_replan_policy.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/deterministic_repair_recovery.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_recovery.py
- Predicted symbols: DeterministicFailureReplanPolicy, AnalyticalCloseExecutor, recover_repair_state, RecoveryRequest, RecoveryDecision, replay_recovery
- Interfaces: RepairRecovery@1, FailureReplanPolicy@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/recovery-vectors.json
- Conflict policy: Residual/provider invocation is structurally absent; restart replays receipts and journals rather than reconstructing synthetic success.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Durable transition state and failure memory exist.
- Effects: Recovers interrupted leases/transactions, retries only typed transient cases, and emits stable abstain/defer/failed outcomes.
- Evidence subset: journal replay, duplicate attempt, lease expiry, crash point, retry decision, rollback state
- Acceptance: Crash/restart at every transition is idempotent; no double mutation, fabricated receipt, weakened gate, or provider/model route occurs.

## DCR-083 Derive all statuses from one content-addressed authority projection

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: supervisor
- Depends on: DCR-010, DCR-080
- Goal id: DCR-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/repair_authority_projection.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_status_projection.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_status_projection.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/supervisor
- Parallel lane: dcr-authority-projection
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/repair_authority_projection.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_status_projection.py
- Predicted symbols: RepairAuthorityProjection, derive_task_status, derive_goal_status
- Interfaces: RepairAuthorityProjection@1, GoalCompletion@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/authority-projection.json
- Conflict policy: Board/objective/baseline/stage/readiness are projections, never independent authorities; contradictory completion reopens.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Live state machine and reconciled legacy evidence exist.
- Effects: Resolves SCA-230-style drift and invalid completions such as aggregates with open dependencies or unpublished handoff.
- Evidence subset: state log root, dependency closure, validation/proof/publication CIDs, projected statuses, contradiction reasons
- Acceptance: One projection deterministically derives all status surfaces; completion requires current PUBLISH and all dependencies, otherwise reopened/blocked/inconclusive.

## DCR-084 Bound supervisor self-improvement by evidence and invariants

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: supervisor
- Depends on: DCR-081, DCR-082, DCR-083
- Goal id: DCR-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/self_improvement.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_self_improvement.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_self_improvement.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/supervisor
- Parallel lane: dcr-self-improve
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/self_improvement.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_self_improvement.py
- Predicted symbols: BoundedSelfImprovement, ImprovementProposal
- Interfaces: BoundedSelfImprovement@1, ImprovementProposal@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/improvement-proposals.json
- Conflict policy: Self-improvement may tune deterministic ordering/bounds or propose reviewed operators; it cannot rewrite policy roots, validators, authority, logic semantics, or model guards.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Selection, recovery, and authority projection are stable.
- Effects: Mines receipt metrics/counterexamples for bounded proposals with invariants, shadow evaluation, proof, rollback, and approval class.
- Evidence subset: baseline/candidate metrics, invariant proofs, changed parameters/operators, shadow receipts, rollback
- Acceptance: No proposal can lower safety floors or self-admit; unchanged or non-improving proposals converge to no-op with zero new work.

## DCR-090 Build hermetic cross-repository contract conformance fixtures

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: DCR-084
- Goal id: DCR-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/hermetic_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_hermetic_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_graph.py, Mcp-Plus-Plus/tests-ts/src/__tests__/swissknife-interop.test.ts, swissknife/test/mcp-plus-plus/dcr090-hermetic-fixtures.test.ts, swissknife/test/mcp-plus-plus/connector-http.test.ts
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_hermetic_conformance.py external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_graph.py; cd swissknife && npm test -- --run test/mcp-plus-plus/dcr090-hermetic-fixtures.test.ts; cd Mcp-Plus-Plus && npm test -- --runInBand tests-ts/src/__tests__/swissknife-interop.test.ts
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/conformance
- Parallel lane: dcr-conformance
- Resource class: cpu-large
- Implementation timeout seconds: 14400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/hermetic_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_hermetic_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_graph.py, Mcp-Plus-Plus/tests-ts/src/__tests__/swissknife-interop.test.ts, swissknife/test/mcp-plus-plus/dcr090-hermetic-fixtures.test.ts, swissknife/test/mcp-plus-plus/connector-http.test.ts
- Predicted symbols: validate_hermetic_conformance, HermeticConformanceReport, SwissKnifeMcpInteropFixture, RealConnectorImportGate
- Interfaces: CrossRepositoryConformance@1, MCP JSON-RPC 2.0, MCP++ Profiles A-F
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/hermetic-conformance.json
- Conflict policy: Monorepo conformance fails if the real connector/import/server is unavailable; standalone-clone skips are separate and cannot make this suite green.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Live supervisor and all operator families are integrated.
- Effects: Uses real connector paths and behaviorally independent compatibility adapters for every contract family.
- Evidence subset: imported module origins, fixture process/config IDs, requests/responses, schemas/CIDs, profile matrix
- Acceptance: Mocks cannot echo requested capabilities or expected detector values; incompatible implementations produce deterministic failing counterexamples.

## DCR-091 Prove live initialize, list, call, and logic equivalence for all servers

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: DCR-023, DCR-090
- Goal id: DCR-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/live_service_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_live_services.py, data/agent_supervisor/deterministic_contract_repair/live-conformance.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_live_services.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/conformance
- Parallel lane: dcr-live-conformance
- Resource class: network-local
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/live_service_conformance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_live_services.py
- Predicted symbols: assess_live_services, LiveConformanceResult, LiveThreeServiceConformance, LogicRouteEquivalence
- Interfaces: LiveMcpConformance@1, tools_dispatch, logic_tools, cec_prove
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/live-conformance.json
- Conflict policy: Require accelerate, datasets, and kit from one manifest; no package is optional and process-local proof cannot substitute for MCP reachability.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Hermetic contract fixtures and exact service manifests pass.
- Effects: Exercises canonical initialize, list, safe call, malformed/unknown calls, profiles, receipts, and logic equivalence against exact live processes.
- Evidence subset: three runtime witnesses, transcripts, local and remote logic receipts, proof reconstruction, model counters
- Acceptance: Required service/profile/tool is proved conformant or typed unsupported per reviewed policy; discovery/transport errors cannot appear as empty success.

## DCR-092 Repair and prove SwissKnife desktop/browser mediation end to end

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: DCR-044, DCR-091
- Goal id: DCR-G100
- Outputs: swissknife/test/mcp-plus-plus/desktop-contract-repair.e2e.test.ts, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_repair_e2e.py
- Validation: cd swissknife && npm test -- --runInBand test/mcp-plus-plus/desktop-contract-repair.e2e.test.ts; python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_repair_e2e.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/conformance
- Parallel lane: dcr-desktop-e2e
- Resource class: browser-local
- Implementation timeout seconds: 21600
- Predicted files: swissknife/test/mcp-plus-plus/desktop-contract-repair.e2e.test.ts, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_mcplusplus_contract_repair_e2e.py
- Predicted symbols: DesktopContractRepairE2E, GovernedMutationAssertion
- Interfaces: DesktopContractRepairE2E@1, GovernedMcpMediator@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/desktop-e2e.json
- Conflict policy: Use a disposable fixture and loopback endpoints; never exercise destructive production tools or bypass execution-time policy.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Live three-service conformance and browser mediator operator pass.
- Effects: Introduces a representative broken contract, runs the full repair state machine, restarts services/browser, and observes the corrected mediated effect.
- Evidence subset: original counterexample, source diff, every transition receipt, browser trace, new graph/proof roots, rollback replay
- Acceptance: Real source changes and contract behavior becomes conformant on a new epoch; raw proxy mutation is denied and every model/provider counter remains zero.

## DCR-093 Add adversarial, mutation, stale-state, and authority negatives

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: DCR-090, DCR-092
- Goal id: DCR-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/evaluation/dcr_adversarial.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_adversarial.py, swissknife/test/mcp-plus-plus/connector-adversarial.test.ts, Mcp-Plus-Plus/tests-ts/src/__tests__/swissknife-adversarial.test.ts
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_adversarial.py; cd swissknife && npm test -- --runInBand test/mcp-plus-plus/connector-adversarial.test.ts
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/conformance
- Parallel lane: dcr-adversarial
- Resource class: cpu-large
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/evaluation/dcr_adversarial.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_adversarial.py, swissknife/test/mcp-plus-plus/connector-adversarial.test.ts, Mcp-Plus-Plus/tests-ts/src/__tests__/swissknife-adversarial.test.ts
- Predicted symbols: evaluate_dcr_adversarial, DcrAdversarialReport, ContractRepairAdversary, AuthorityMutationSuite
- Interfaces: AdversarialConformance@1, MutationScore@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/adversarial-report.json
- Conflict policy: Tests mutate fixtures only and demand fail-closed outcomes; no safety threshold may be weakened to improve score.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Successful end-to-end fixture establishes positive control.
- Effects: Covers malformed envelopes, wrong status/ID/version, overclaimed capabilities, bad CIDs/schemas/receipts, policy outage, mixed roots, stale spans, lease races, crashes, and forged/synthetic evidence.
- Evidence subset: mutation ID, expected disposition, actual state/receipt, killed-survivor matrix, rollback verification
- Acceptance: Every safety mutation is killed; unknown/unsupported/error never grants mutation/completion and provider/model tripwires remain untouched.

## DCR-094 Reach a stable contract fixed point and supersede legacy repair rows

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: DCR-091, DCR-092, DCR-093
- Goal id: DCR-G100
- Outputs: data/agent_supervisor/deterministic_contract_repair/fixed-point.json, generated/ipfs_accelerate_contract_repairs.todo.md, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_fixed_point.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_fixed_point.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/conformance
- Parallel lane: dcr-fixed-point
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 21600
- Predicted files: generated/ipfs_accelerate_contract_repairs.todo.md, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_fixed_point.py
- Predicted symbols: ContractRepairFixedPoint, supersede_legacy_repairs
- Interfaces: ContractRepairFixedPoint@1, RepairBacklogProjection@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/fixed-point.json
- Conflict policy: Preserve unsupported/review-required findings explicitly; do not close them as repaired or delete historical evidence.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Positive, live, desktop, and adversarial suites pass.
- Effects: Reconciles all findings by canonical key, supersedes/deduplicates the 13 ambiguous-anchor legacy rows, and runs two unchanged full epochs.
- Evidence subset: initial/final finding sets, supersession map, published repairs, unresolved typed rows, epoch roots
- Acceptance: All supported repairable findings are proved valid/repaired; two unchanged epochs emit zero tasks/edits and identical authoritative state roots.

## DCR-100 Benchmark deterministic repair precision, safety, and cost

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: evaluation
- Depends on: DCR-094
- Goal id: DCR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/evaluation/dcr_benchmark.py, data/agent_supervisor/deterministic_contract_repair/benchmark.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_benchmark.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_benchmark.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/release
- Parallel lane: dcr-benchmark
- Resource class: cpu-large
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/evaluation/dcr_benchmark.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_benchmark.py
- Predicted symbols: DeterministicRepairBenchmark, RepairSafetyMetrics
- Interfaces: DeterministicRepairBenchmark@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/benchmark.json
- Conflict policy: Count abstention separately from false success; exclude cached/warm artifacts unless the cache is explicitly measured.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Stable fixed point and mutation corpus exist.
- Effects: Measures detection/repair precision and recall, false completion/mutation, rollback, convergence, latency, CPU/memory/disk, proof reuse, zero-LLM enforcement, and cold imports across every interpreter version declared by the package.
- Evidence subset: corpus roots, cold/warm runs, confusion matrices, resource metrics, safety-floor counters
- Acceptance: Zero false completion, unauthorized mutation, mixed-root publication, unobserved transition, and model/provider calls; every declared Python version imports the supervisor without newer-stdlib leakage; thresholds are reviewed before rollout.

## DCR-101 Run report-only and shadow execution against current repositories

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: rollout
- Depends on: DCR-100
- Goal id: DCR-G110
- Outputs: data/agent_supervisor/deterministic_contract_repair/shadow-report.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_shadow.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_shadow.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/release
- Parallel lane: dcr-shadow
- Resource class: cpu-large
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_shadow.py
- Predicted symbols: DeterministicRepairShadowRun, compare_shadow_to_truth
- Interfaces: RepairShadowReport@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/shadow-report.json
- Conflict policy: Read-only current checkout; preview patches/worktrees are discarded and never published or projected completed.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Benchmark safety floors pass.
- Effects: Compares deterministic findings/proposals to current tests, maintainers’ classifications, and known legacy evidence without mutating sources.
- Evidence subset: forest/runtime roots, findings, proposed operators, abstentions, comparison labels, resource/model counters
- Acceptance: No writes outside runtime paths; every proposal is explainable/replayable and shadow metrics meet reviewed release thresholds.

## DCR-102 Enable fixture-apply then auto-safe canary mode

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: rollout
- Depends on: DCR-101
- Goal id: DCR-G110
- Outputs: config/deterministic_contract_repair_policy.json, data/agent_supervisor/deterministic_contract_repair/canary-report.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_canary.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_canary.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/release
- Parallel lane: dcr-canary
- Resource class: cpu-large
- Implementation timeout seconds: 21600
- Predicted files: config/deterministic_contract_repair_policy.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_canary.py
- Predicted symbols: RepairExecutionMode, AutoSafeAdmission
- Interfaces: DeterministicRepairPolicy@1, AutoSafeAdmission@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/canary-report.json
- Conflict policy: Progress report_only→fixture_apply→auto_safe only; cross-repo semantics, policy/authority, migrations, ambiguous anchors, unsupported logic, and unmodeled effects always abstain for review.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Shadow thresholds pass and rollback/restart drills are current.
- Effects: Applies an allowlisted low-risk operator subset in isolated canary branches with rate/error/rollback circuit breakers.
- Evidence subset: mode transition, allowlist/policy root, canary repairs, circuit breaker, rollback drills, safety counters
- Acceptance: Canary meets thresholds across the review window; any safety-floor breach disables apply and leaves report-only evidence.

## DCR-103 Publish the deterministic repair release and operator policy

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: release
- Depends on: DCR-102
- Goal id: DCR-G110
- Outputs: implementation_plan/docs/deterministic-contract-repair-operations.md, data/agent_supervisor/deterministic_contract_repair/release.json, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_release.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_release.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/release
- Parallel lane: dcr-release
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: implementation_plan/docs/deterministic-contract-repair-operations.md, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_release.py
- Predicted symbols: DeterministicRepairRelease, verify_release
- Interfaces: DeterministicRepairRelease@1, OperatorPolicyRoot@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/release.json
- Conflict policy: Release receipt names unresolved typed gaps and exact auto-safe boundary; no compatibility claim exceeds live/reconstructed evidence.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Canary window and all safety floors pass.
- Effects: Pins code/config/operator/toolchain/test/benchmark roots, runbook, rollback procedure, service manifest, and signed review decisions.
- Evidence subset: root/pin matrix, release DAG, conformance/fixed-point/benchmark/canary CIDs, unresolved rows
- Acceptance: Fresh clean clones reproduce the release, repair fixture, and proof with zero model/provider calls and no untracked implementation dependency.

## DCR-104 Detect incremental drift and invalidate affected evidence continuously

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: release
- Depends on: DCR-103
- Goal id: DCR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/drift_monitor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_drift_monitor.py, data/agent_supervisor/deterministic_contract_repair/drift-policy.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_drift_monitor.py
- Board namespace: deterministic-swissknife-mcplusplus-contract-repair-v1
- Bundle: dcr/release
- Parallel lane: dcr-drift
- Resource class: cpu-medium
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/drift_monitor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_drift_monitor.py
- Predicted symbols: ContractDriftMonitor, AffectedEvidenceClosure
- Interfaces: ContractDriftMonitor@1, ProofInvalidation@1
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, Mcp-Plus-Plus, swissknife
- Generated artifacts: data/agent_supervisor/deterministic_contract_repair/drift-policy.json
- Conflict policy: Incremental scans may invalidate/reopen but cannot auto-weaken contracts, add operator semantics, or infer service health from stale receipts.
- Symbolic first: true
- LLM context budget bytes: 262144
- Provider role: grok-primary-implement, codex-fallback-implement
- Context budget tokens: 16384
- Implementation mode: ordered_provider
- Runtime model calls: 0
- Preconditions: Reproducible release roots and dependency graph exist.
- Effects: Maps source/config/toolchain/runtime changes to affected graph edges, proofs, plans, tasks, goals, and required live probes.
- Evidence subset: change root, dependency closure, invalidations, rechecks, new findings, status projection
- Acceptance: Relevant drift reopens exactly affected state; irrelevant changes reuse reconstructed evidence; two unchanged scans remain a no-op with zero model/provider calls.

