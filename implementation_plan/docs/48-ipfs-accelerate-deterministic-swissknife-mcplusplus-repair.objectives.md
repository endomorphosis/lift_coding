# Deterministic SwissKnife ↔ MCP++ Contract Repair Objective Heap (DCR)

Machine-ingestible goal state for `ipfs_accelerate_py.agent_supervisor`.
The executable task projection is
`implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.todo.md`
with task prefix `## DCR-`. The reviewed architecture is
`implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md`.

## North star

Enable the agent supervisor to close SwissKnife desktop ↔ MCP++ contract
failures by using current multi-root evidence, `ipfs_datasets_py.logic`, a
finite deterministic repair operator library, deterministic Doctor diagnosis,
and proof-carrying Planner execution, with zero language-model calls.

## Goal tree

```text
DCR-G000  Deterministic desktop↔MCP++ repair fixed point
|-- DCR-G010  No-LLM authority, dispositions, and multi-root ownership
|-- DCR-G020  Current-tree evidence and analyzer health
|-- DCR-G030  Cross-repository contract catalog and runtime identity
|-- DCR-G040  Datasets logic kernel, obligations, and proof evidence
|-- DCR-G050  Typed deterministic repair operator library
|-- DCR-G060  Production deterministic Doctor
|-- DCR-G070  Proof-carrying deterministic Planner
|-- DCR-G080  Transactional repair, validation, and merge
|-- DCR-G090  Live supervisor activation and bounded self-improvement
|-- DCR-G100  SwissKnife desktop/MCP++ conformance and repair fixed point
`-- DCR-G110  Evaluation, staged rollout, release, and continuous drift
```

## DCR-G000 Deterministic desktop↔MCP++ repair fixed point

- Status: active
- Parent:
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: deterministic-contract-repair
- Bundle: dcr/root
- Goal: Produce one current-tree, no-LLM repair loop that discovers, proves, repairs, validates, and closes SwissKnife desktop to MCP++ contract drift across all owning repositories.
- Evidence: dcr/control-plane@1, dcr/no-llm@1, dcr/contract-fixed-point@1, dcr/release@1
- Acceptance criteria: dcr/control-plane@1; dcr/no-llm@1; dcr/contract-fixed-point@1; dcr/release@1
- Outputs: implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.objectives.md, implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.todo.md, config/deterministic_swissknife_mcplusplus_repair_scheduler.json
- Validation: python3 scripts/validate_deterministic_contract_repair_board.py --check-all
- Acceptance: Every child goal has current evidence bound to one forest and policy root; two unchanged epochs emit no new repair; all authoritative epochs contain zero model, LLM, and provider calls.
- Gap task: DCR-000 through DCR-104
- Refinement: Reuse SCA, RPR, WPD, Doctor, Planner, proof, and autonomous-repair components; prohibit parallel replacement frameworks.
- Embedding query: deterministic SwissKnife desktop MCP++ repair fixed point no LLM agent supervisor
- AST query: Locate SCA baseline, contract catalog, deterministic Doctor, FormalPlanCompiler, repair materializer, and supervisor selection entrypoints.

## DCR-G010 No-LLM authority, dispositions, and multi-root ownership

- Status: active
- Parent: DCR-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: authority
- Bundle: dcr/authority
- Goal: Seal the deterministic-only execution boundary, authority ladder, terminal dispositions, current-snapshot requirements, and repository ownership rules before any repair can run.
- Evidence: dcr/no-llm-policy@1, dcr/disposition@1, dcr/multi-root-ownership@1, dcr/capability-manifest@1
- Acceptance criteria: dcr/no-llm-policy@1; dcr/disposition@1; dcr/multi-root-ownership@1; dcr/capability-manifest@1
- Outputs: config/deterministic_contract_repair_authority.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/contracts.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/capabilities.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_authority.py external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_repair_capabilities.py
- Acceptance: Model imports and calls are blocked; unknown capability and ambiguous ownership cannot become mutation or completion authority; every receipt binds exact roots.
- Gap task: DCR-001, DCR-002, DCR-003, DCR-004
- Refinement: Align with ImplementationDisposition, RPR admission, runtime identity, and existing authority policies.
- Embedding query: no LLM authority disposition multi root ownership capability receipt
- AST query: ImplementationDisposition, task_execution_policy, sca_rpr_admission, repository_forest, provider routes.

## DCR-G020 Current-tree evidence and analyzer health

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G010
- Fib priority: 3
- Priority: P0
- Track: evidence
- Bundle: dcr/evidence
- Goal: Replace stale or cross-snapshot assumptions with a healthy current forest, reconciled WPD/SCA evidence, complete provider roots, and exact parser/registration accounting.
- Evidence: dcr/current-state-reconciliation@1, dcr/forest@1, dcr/analyzer-health@1, dcr/provider-surface-index@1, dcr/desktop-expectation-index@1
- Acceptance criteria: dcr/current-state-reconciliation@1; dcr/forest@1; dcr/analyzer-health@1; dcr/provider-surface-index@1; dcr/desktop-expectation-index@1
- Outputs: data/agent_supervisor/deterministic_contract_repair/current-state.json, data/agent_supervisor/deterministic_contract_repair/forest.json, data/agent_supervisor/deterministic_contract_repair/analyzer-health.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_current_evidence.py external/ipfs_accelerate/test/api/test_agent_supervisor_production_multi_root_index.py
- Acceptance: Required roots, overlays, parser rows, registrations, and desktop declarations share one current snapshot; incomplete measurement withholds parity and completion.
- Gap task: DCR-010, DCR-011, DCR-012, DCR-013, DCR-014
- Refinement: Revalidate existing WPD/SCA modules before creating new code.
- Embedding query: current tree evidence analyzer health provider surface desktop expected contract
- AST query: index_repository_contracts, repository_forest, provider_surface_health, mcp_contract_catalog.

## DCR-G030 Cross-repository contract catalog and runtime identity

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G020
- Fib priority: 5
- Priority: P0
- Track: contract-catalog
- Bundle: dcr/catalog
- Goal: Normalize declarations and observations across SwissKnife and MCP++ providers into one content-addressed graph with exact runtime witnesses and deterministic mismatch classes.
- Evidence: dcr/identity@1, dcr/contract-graph@1, dcr/runtime-witness@1, dcr/live-observation@1, dcr/mismatch@1
- Acceptance criteria: dcr/identity@1; dcr/contract-graph@1; dcr/runtime-witness@1; dcr/live-observation@1; dcr/mismatch@1
- Outputs: data/agent_supervisor/deterministic_contract_repair/mcp_contract_graph.json, data/agent_supervisor/deterministic_contract_repair/runtime-witness.json, data/agent_supervisor/deterministic_contract_repair/mcp_contract_mismatch_findings.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_graph.py external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_live_observer.py
- Acceptance: Every mandatory contract edge has declaration and observation provenance; mixed roots, pseudo-CIDs, duplicate aliases, and expected-only surfaces remain explicit failures.
- Gap task: DCR-020, DCR-021, DCR-022, DCR-023, DCR-024
- Refinement: Extend the existing catalog, evidence compiler, resolver, runtime witness, and mismatch analyzer.
- Embedding query: normalized MCP contract graph runtime identity expected actual mismatch
- AST query: mcp_contract_catalog, runtime_contract_evidence_compiler, mcplusplus_contract_resolver, mcp_live_conformance.

## DCR-G040 Datasets logic kernel, obligations, and proof evidence

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G030
- Fib priority: 5
- Priority: P0
- Track: logic-proof
- Bundle: dcr/logic
- Goal: Compile normalized contracts into the exact `ipfs_datasets_py.logic` IR portfolio and emit replayable proof, refutation, counterexample, unknown, and invalidation evidence.
- Evidence: dcr/ir-normalization@1, dcr/obligation@1, dcr/prover-portfolio@1, dcr/counterexample@1, dcr/proof-cache@1, dcr/unknown-gate@1
- Acceptance criteria: dcr/ir-normalization@1; dcr/obligation@1; dcr/prover-portfolio@1; dcr/counterexample@1; dcr/proof-cache@1; dcr/unknown-gate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ir_integration.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/multi_prover_router.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_logic_kernel.py external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py
- Acceptance: Only capability-qualified deterministic backends run; accepted proofs reconstruct under policy; unknown and unsupported never become proved or repairable.
- Gap task: DCR-030, DCR-031, DCR-032, DCR-033, DCR-034, DCR-035
- Refinement: Use IR adapters and existing proof caches; do not create a second theorem or authority lattice.
- Embedding query: datasets logic IR MCP contract obligations proof counterexample reconstruction
- AST query: ir_registry, ir_adapters, mcp_contract_obligations, mcp_contract_prover, multi_prover_router.

## DCR-G050 Typed deterministic repair operator library

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G040
- Fib priority: 8
- Priority: P0
- Track: repair-operators
- Bundle: dcr/operators
- Goal: Provide a finite reviewed operator set for aliases, registration, schemas, dispatch, transport, UI/ORB/IDL, authorization/effects, and generated artifacts.
- Evidence: dcr/operator-registry@1, dcr/registry-repair@1, dcr/schema-repair@1, dcr/dispatch-repair@1, dcr/transport-repair@1, dcr/ui-repair@1, dcr/safety-repair@1, dcr/codegen-roundtrip@1
- Acceptance criteria: dcr/operator-registry@1; dcr/registry-repair@1; dcr/schema-repair@1; dcr/dispatch-repair@1; dcr/transport-repair@1; dcr/ui-repair@1; dcr/safety-repair@1; dcr/codegen-roundtrip@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/operators, external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operators.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_contract_operators.py
- Acceptance: Each operator has a closed input schema, exact write set, applicability proof, preview, inverse/rollback, and mutation tests; arbitrary source generation is absent.
- Gap task: DCR-040 through DCR-047
- Refinement: Refactor current repair materialization into typed operators where possible.
- Embedding query: deterministic repair operator registry schema dispatch transport UI ORB IDL
- AST query: autonomous_repair materialize edit_plan interface_alias_registry mcp_surface_resolution.

## DCR-G060 Production deterministic Doctor

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G050
- Fib priority: 8
- Priority: P0
- Track: doctor
- Bundle: dcr/doctor
- Goal: Make the default Doctor diagnose current contract findings, select only applicable deterministic transforms, and prove fixed-point progress or typed abstention.
- Evidence: dcr/doctor-factory@1, dcr/doctor-diagnosis@1, dcr/doctor-plan@1, dcr/doctor-fixed-point@1
- Acceptance criteria: dcr/doctor-factory@1; dcr/doctor-diagnosis@1; dcr/doctor-plan@1; dcr/doctor-fixed-point@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/default_doctor_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_doctor_bridge.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/worker_doctor_bridge.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_default_doctor_factory.py external/ipfs_accelerate/test/api/test_agent_supervisor_worker_doctor_bridge.py external/ipfs_accelerate/test/api/test_agent_supervisor_deterministic_doctor_fixed_point.py
- Acceptance: Doctor finds the earliest broken edge, attaches minimal evidence, never invents an operator, and terminates repeated no-progress attempts without a model call.
- Gap task: DCR-050, DCR-051, DCR-052, DCR-053
- Refinement: Activate and harden existing Doctor factories and bridges rather than adding another service.
- Embedding query: deterministic Doctor contract finding transform fixed point abstention
- AST query: default_doctor_factory, DeterministicDoctorService, sca_doctor_bridge, worker_doctor_bridge.

## DCR-G070 Proof-carrying deterministic Planner

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G060
- Fib priority: 13
- Priority: P0
- Track: planner
- Bundle: dcr/planner
- Goal: Compile Doctor transforms and proof obligations into ownership-safe, resource-bounded task DAGs with admitted candidates and typed retry memory.
- Evidence: dcr/planner-factory@1, dcr/plan-dag@1, dcr/candidate-portfolio@1, dcr/replan@1, dcr/resource-schedule@1
- Acceptance criteria: dcr/planner-factory@1; dcr/plan-dag@1; dcr/candidate-portfolio@1; dcr/replan@1; dcr/resource-schedule@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/default_planner_factory.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/formal_plan_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/symbolic_candidate_planner.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_default_planner_factory.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_planner.py
- Acceptance: Every executable node binds evidence, operator, owner, write set, validation, rollback, proof transition, and dependencies; no provider/model node is representable.
- Gap task: DCR-060, DCR-061, DCR-062, DCR-063, DCR-064
- Refinement: Extend formal compiler/validator/replanner and proof-carrying planner contracts.
- Embedding query: proof carrying deterministic planner repair DAG ownership retry memory
- AST query: FormalPlanCompiler, FormalPlanValidator, FormalReplanner, SymbolicCandidatePlanner, AdaptivePlanner.

## DCR-G080 Transactional repair, validation, and merge

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G070
- Fib priority: 13
- Priority: P0
- Track: execution
- Bundle: dcr/execution
- Goal: Admit exact repair packets, materialize typed structural edits in isolated owner worktrees, validate/re-prove, roll back failures, and emit merge/pin provenance.
- Evidence: dcr/repair-admission@1, dcr/materialization@1, dcr/transaction@1, dcr/validation@1, dcr/merge-provenance@1
- Acceptance criteria: dcr/repair-admission@1; dcr/materialization@1; dcr/transaction@1; dcr/validation@1; dcr/merge-provenance@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/sca_rpr_admission.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/materialize.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/engine.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_sca_rpr_admission.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_transaction.py
- Acceptance: Stale, ambiguous, dirty-unbound, cross-root, out-of-scope, or non-invertible edits fail before write; failed validation leaves no promoted mutation.
- Gap task: DCR-070, DCR-071, DCR-072, DCR-073, DCR-074
- Refinement: Reuse CodeEditPacket, repair packets, worktree, merge resolver, and post-merge validation.
- Embedding query: admitted repair packet structural edit worktree rollback reproof merge provenance
- AST query: sca_rpr_admission, autonomous_repair.engine, materialize, worktrees, merge_resolver, post_merge_validation.

## DCR-G090 Live supervisor activation and bounded self-improvement

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G080
- Fib priority: 21
- Priority: P0
- Track: supervisor
- Bundle: dcr/supervisor
- Goal: Put deterministic repair before provider invocation in selection, refill, retry, rescue, completion, and bounded supervisor self-improvement paths.
- Evidence: dcr/preimplementation-gate@1, dcr/selection@1, dcr/rescue@1, dcr/completion@1, dcr/self-improvement@1
- Acceptance criteria: dcr/preimplementation-gate@1; dcr/selection@1; dcr/rescue@1; dcr/completion@1; dcr/self-improvement@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_provider_gate.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/pre_implementation_kernel.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/repair_authority_projection.py
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_pre_implementation_kernel.py external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_supervisor_activation.py
- Acceptance: DCR work cannot enter a model route; selection uses deterministic dispositions; rescue and retries cannot thrash; self-improvement consumes typed receipts and cannot edit control policy.
- Gap task: DCR-080, DCR-081, DCR-082, DCR-083, DCR-084
- Refinement: Reconcile WPD implementation and current live supervisor wiring first.
- Embedding query: live supervisor deterministic preimplementation selection refill rescue self improvement
- AST query: pre_implementation_kernel, implementation_daemon, implementation_supervisor, authoritative_completion, refill, rescue.

## DCR-G100 SwissKnife desktop/MCP++ conformance and repair fixed point

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G090
- Fib priority: 21
- Priority: P0
- Track: conformance
- Bundle: dcr/conformance
- Goal: Prove hermetic and live MCP++ discovery/call behavior, desktop UI/ORB/IDL behavior, adversarial failure handling, and closure of the current 13 generated repair tasks.
- Evidence: dcr/hermetic-conformance@1, dcr/live-conformance@1, dcr/desktop-e2e@1, dcr/adversarial@1, dcr/current-repairs-fixed-point@1
- Acceptance criteria: dcr/hermetic-conformance@1; dcr/live-conformance@1; dcr/desktop-e2e@1; dcr/adversarial@1; dcr/current-repairs-fixed-point@1
- Outputs: data/agent_supervisor/deterministic_contract_repair/conformance, data/agent_supervisor/deterministic_contract_repair/fixed-point.json
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_conformance.py && npm --prefix swissknife test -- --runInBand
- Acceptance: Representative safe calls reach exact handlers; invalid behavior fails closed; desktop behavior matches canonical descriptors; current repairs close or are traceably superseded; unchanged rescan emits zero new edits.
- Gap task: DCR-090, DCR-091, DCR-092, DCR-093, DCR-094
- Refinement: Keep hermetic and loopback-live evidence distinct and bind both to current runtime identity.
- Embedding query: SwissKnife desktop MCP++ conformance tools list call fixed point
- AST query: SwissKnife MCP client registry desktop apps ORB IDL, MCP++ dispatchers, mcp_live_conformance.

## DCR-G110 Evaluation, staged rollout, release, and continuous drift

- Status: active
- Parent: DCR-G000
- Depends on: DCR-G100
- Fib priority: 34
- Priority: P0
- Track: release
- Bundle: dcr/release
- Goal: Measure deterministic repair quality and safety, shadow the live system, promote only safe operator classes, issue one terminal release receipt, and detect future drift incrementally.
- Evidence: dcr/benchmark@1, dcr/shadow@1, dcr/auto-safe@1, dcr/release@1, dcr/continuous-drift@1
- Acceptance criteria: dcr/benchmark@1; dcr/shadow@1; dcr/auto-safe@1; dcr/release@1; dcr/continuous-drift@1
- Outputs: data/agent_supervisor/deterministic_contract_repair/benchmark.json, data/agent_supervisor/deterministic_contract_repair/release.json, implementation_plan/docs/deterministic-contract-repair-operations.md
- Validation: python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_dcr_release.py
- Acceptance: Precision and safety floors pass; shadow and auto-safe receipts bind the same policies; release proves zero model calls and current fixed point; later drift invalidates only affected proofs and tasks.
- Gap task: DCR-100, DCR-101, DCR-102, DCR-103, DCR-104
- Refinement: Roll back to report-only on any floor violation or stale root.
- Embedding query: deterministic repair benchmark shadow auto safe release continuous drift
- AST query: logic_repair_rollout, deterministic_doctor_release, worker_planner_doctor_release, proof cache invalidation.
