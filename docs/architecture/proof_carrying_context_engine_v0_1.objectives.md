# Proof-Carrying Context Engine v0.1 Objective Heap

This is the authoritative intent hierarchy for the v0.1 integration program.
The executable projection is
`docs/architecture/proof_carrying_context_engine_v0_1.todo.md` with task prefix
`## PCCE-`. Generated graphs, bundles, datasets, and JSON boards are derived
projections and do not supersede this heap or task receipts.

## Goal tree

```text
PCCE-G000  Installable Proof-Carrying Context Engine v0.1
|-- PCCE-G100  A: implementation inventory and contract freeze
|-- PCCE-G200  B: stable governed runtime facade
|-- PCCE-G300  C: provider-neutral agent and patch adapters
|-- PCCE-G400  D: one-command CLI and reports
|-- PCCE-G500  E: installability and clean packaging
|-- PCCE-G600  F: frozen external generalization benchmark
|-- PCCE-G700  G: security and trust-boundary hardening
`-- PCCE-G800  H: release qualification and go/no-go
```

## PCCE-G000 Installable Proof-Carrying Context Engine v0.1

- Status: active
- Parent:
- Parent goal IDs JSON: []
- Depends on:
- Dependencies JSON: []
- Fib priority: 1
- Priority: P0
- Track: proof-carrying-context-engine-v0.1
- Bundle: proof-context/root
- Parallel lane: coordinator
- Resource class: coordinator
- Goal: Integrate the existing semantic-compression, incremental-verification, model-routing, assurance, and proof-sealing candidates into one installable provider-neutral sidecar runtime and CLI, then qualify it no higher than current evidence permits.
- Producing tasks: PCCE-000, PCCE-001, PCCE-002, PCCE-003, PCCE-004, PCCE-005, PCCE-006, PCCE-007, PCCE-008, PCCE-009, PCCE-010, PCCE-011, PCCE-012, PCCE-013, PCCE-014, PCCE-015, PCCE-016, PCCE-017, PCCE-018, PCCE-019, PCCE-020, PCCE-021, PCCE-022, PCCE-023, PCCE-024, PCCE-025, PCCE-030, PCCE-031, PCCE-032, PCCE-033, PCCE-034, PCCE-035, PCCE-040, PCCE-041, PCCE-042, PCCE-043, PCCE-044, PCCE-045, PCCE-050, PCCE-051, PCCE-052, PCCE-053, PCCE-054, PCCE-055, PCCE-056, PCCE-057, PCCE-060, PCCE-061, PCCE-062, PCCE-063, PCCE-064, PCCE-065, PCCE-066, PCCE-067, PCCE-068, PCCE-070, PCCE-071, PCCE-072, PCCE-073, PCCE-074, PCCE-075, PCCE-076, PCCE-079, PCCE-080, PCCE-081, PCCE-082, PCCE-083
- Evidence: artifacts/proof_carrying_context_engine/release/final_supervisor_report.json
- Evidence requirements JSON: ["exact four-repository source manifest", "installable package artifacts", "runtime and CLI conformance", "frozen benchmark results", "security gate", "release manifest", "qualification decision"]
- Evidence criteria: Every accepted operation follows the governed lifecycle; production and supervised modes reject stale, simulated, invalid, forged, unavailable, or insufficient evidence; package installation requires no sibling source trees; and the final level and recommendation are computed from current-tree evidence.
- Evidence source policy: Documentation, branch names, historical boards, model output, path presence, task status, ordinary test exit alone, and simulated evidence are non-authoritative. Accept exact Git/tree identities, immutable artifacts, current validations, independent review, trusted receipts, seals, benchmark records, and release gates.
- Outputs: artifacts/proof_carrying_context_engine/release/final_supervisor_report.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/release/final_supervisor_report.json"]
- Validation: python scripts/validate_proof_carrying_context_engine_board.py --check-all
- Validation commands JSON: ["python scripts/validate_proof_carrying_context_engine_board.py --check-all"]
- Acceptance: PCCE-083 records every task disposition and produces an explicit evidence-based proceed, proceed-with-restrictions, or no-go decision; no production-readiness claim is inferred from component completion.
- Gap task: Execute the smallest ready PCCE task under the frozen DAG, owned-path conflict plan, leases, fences, isolated worktrees, and independent validation.

## PCCE-G100 A: implementation inventory and contract freeze

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on:
- Dependencies JSON: []
- Fib priority: 2
- Priority: P0
- Track: inventory-contracts
- Bundle: proof-context/epic-a
- Parallel lane: inventory-contracts
- Resource class: io-analysis
- Goal: Establish exact canonical implementations and ownership, freeze v0.1 contracts, and remove only integration blockers required by the runtime.
- Producing tasks: PCCE-000, PCCE-001, PCCE-002, PCCE-003, PCCE-004, PCCE-005, PCCE-006, PCCE-007, PCCE-008, PCCE-009, PCCE-010, PCCE-011, PCCE-012, PCCE-013, PCCE-014, PCCE-015, PCCE-016, PCCE-017, PCCE-018, PCCE-019
- Evidence: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json
- Evidence requirements JSON: ["four repository inventories", "candidate-ref disposition map", "ownership violation and migration map", "schema/version matrix", "canonical vectors", "exact-object acquisition or external-block receipts", "datasets proof and assurance foundations", "kit proof and assurance stores", "public sealer and assurance convergence", "selected-test soundness repair", "install blocker report", "Epic A acceptance receipt"]
- Evidence criteria: Code, imports, tests, packaging, and exact Git objects support every selected implementation; WIP candidates are not promoted by name; all frozen contracts have version, canonicalization, CID, vector, and migration rules.
- Evidence source policy: README and historical task claims are corroboration only; missing code/tests or dirty/unpublished candidate state is reported unavailable or WIP.
- Outputs: artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/contracts/epic_a_gate.json"]
- Validation: python scripts/validate_proof_carrying_context_engine_board.py --check-all
- Validation commands JSON: ["python scripts/validate_proof_carrying_context_engine_board.py --check-all"]
- Acceptance: PCCE-011 proves inventories, ownership, contract parity, blocker repairs, and exact post-A source identities without broad legacy refactoring.
- Gap task: Resolve the smallest missing inventory, ownership, schema, vector, CID, packaging, or exact-tree fact.

## PCCE-G200 B: stable governed runtime facade

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G100
- Dependencies JSON: ["PCCE-G100"]
- Fib priority: 3
- Priority: P0
- Track: runtime
- Bundle: proof-context/epic-b
- Parallel lane: runtime
- Resource class: cpu-medium
- Goal: Implement one stable provider-neutral `ProofCarryingContextEngine` facade and a non-bypassable, resumable, fail-closed patch lifecycle.
- Producing tasks: PCCE-020, PCCE-021, PCCE-022, PCCE-023, PCCE-024, PCCE-025
- Evidence: artifacts/proof_carrying_context_engine/runtime/epic_b_gate.json
- Evidence requirements JSON: ["closed modes/status/errors", "semantic bridge", "kit persistence bridge", "isolated lifecycle", "public facade", "failure and resume E2E"]
- Evidence criteria: Initialization, scan, status, plan, ContextPack, route, patch, verify, expand, assure, seal, report, and resume work through one lifecycle; accepted production results cannot skip stages.
- Evidence source policy: Adapter self-report, generic dictionaries, mocks, simulated proof, stale state, and unsealed patches do not authorize success.
- Outputs: artifacts/proof_carrying_context_engine/runtime/epic_b_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/runtime/epic_b_gate.json"]
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context_engine
- Validation commands JSON: ["python -m pytest -q external/ipfs_accelerate/test/proof_context_engine"]
- Acceptance: PCCE-025 passes the governed lifecycle and restart suite, including rejection of every stale/simulated/unavailable/partial-effect fixture.
- Gap task: Repair the smallest typed runtime, lifecycle, persistence, isolation, resume, or fail-closed defect.

## PCCE-G300 C: provider-neutral agent and patch adapters

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G200
- Dependencies JSON: ["PCCE-G200"]
- Fib priority: 5
- Priority: P0
- Track: adapters
- Bundle: proof-context/epic-c
- Parallel lane: adapters
- Resource class: process-model
- Goal: Provide bounded Codex, command, replay, and external-patch adapters behind one provider-neutral proposal contract, without granting branch or approval authority.
- Producing tasks: PCCE-030, PCCE-031, PCCE-032, PCCE-033, PCCE-034, PCCE-035
- Evidence: artifacts/proof_carrying_context_engine/adapters/epic_c_gate.json
- Evidence requirements JSON: ["adapter schema", "Codex cancellation/cost receipt", "command sandbox receipt", "deterministic replay vectors", "external patch policy", "cross-adapter conformance"]
- Evidence criteria: Every proposal binds provider/model/revision/tier/patch/files/tokens/cache/latency/cost/artifact/live-state and remains non-authoritative until independent engine acceptance.
- Evidence source policy: Agent output and process exit are untrusted proposals; replay/simulation are permanently labelled and excluded from live claims.
- Outputs: artifacts/proof_carrying_context_engine/adapters/epic_c_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/adapters/epic_c_gate.json"]
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/adapters
- Validation commands JSON: ["python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/adapters"]
- Acceptance: PCCE-035 proves bounded arguments, allowlists, cancellation, timeouts, log limits, identity preservation, no implicit credentials, and no adapter self-approval.
- Gap task: Close the smallest provider-neutral contract, cancellation, sandbox, replay, external patch, or receipt gap.

## PCCE-G400 D: one-command CLI and reports

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G200
- Dependencies JSON: ["PCCE-G200"]
- Fib priority: 8
- Priority: P0
- Track: cli-reporting
- Bundle: proof-context/epic-d
- Parallel lane: cli-reporting
- Resource class: cpu-small
- Goal: Expose the complete governed lifecycle through a stable `proof-context` CLI with JSON schemas, exit codes, correlation IDs, artifact identities, and honest human reports.
- Producing tasks: PCCE-040, PCCE-041, PCCE-042, PCCE-043, PCCE-044
- Evidence: artifacts/proof_carrying_context_engine/cli/epic_d_gate.json
- Evidence requirements JSON: ["CLI schema and exit-code vectors", "read command E2E", "mutation command E2E", "human report golden files", "transport parity receipt"]
- Evidence criteria: All required commands support stable JSON and human output; savings distinguish observed versus baseline-estimated values; failures map to the closed taxonomy and nonzero exits.
- Evidence source policy: Console prose, missing fields, generic success dictionaries, and estimated savings without a declared baseline cannot satisfy reporting.
- Outputs: artifacts/proof_carrying_context_engine/cli/epic_d_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/cli/epic_d_gate.json"]
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/cli
- Validation commands JSON: ["python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/cli"]
- Acceptance: PCCE-044 runs the example command set, validates JSON schemas/exit codes/trace IDs, and compares a complete human report to golden evidence.
- Gap task: Repair the smallest CLI command, output-schema, exit-code, trace, artifact, or report-truthfulness defect.

## PCCE-G500 E: installability and clean packaging

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G300, PCCE-G400
- Dependencies JSON: ["PCCE-G300", "PCCE-G400"]
- Fib priority: 13
- Priority: P0
- Track: packaging
- Bundle: proof-context/epic-e
- Parallel lane: packaging
- Resource class: io-build
- Goal: Produce immutable installable artifacts, narrow extras, reproducible manifests, and a credential-free synthetic example without sibling/source-path assumptions.
- Producing tasks: PCCE-045, PCCE-050, PCCE-051, PCCE-052, PCCE-053, PCCE-054, PCCE-055, PCCE-056, PCCE-057
- Evidence: artifacts/proof_carrying_context_engine/install/epic_e_gate.json
- Evidence requirements JSON: ["four package profiles", "datasets, kit, accelerator, and data-only MCP++ contract artifacts", "SelfHostingQualificationHarness package surface", "artifact hashes", "dependency locks", "SBOM", "environment manifest", "example workflow", "clean-install matrix"]
- Evidence criteria: Core, verification, Codex, supported local, and evaluation profiles install from immutable artifacts in a clean environment; core remains narrow; no editable, sibling, recursive-submodule, arbitrary path, or mutable-main requirement remains.
- Evidence source policy: Editable source installs and already-populated developer environments are diagnostic only, not release evidence.
- Outputs: artifacts/proof_carrying_context_engine/install/epic_e_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/install/epic_e_gate.json"]
- Validation: python -m pytest -q tests/proof_context_engine/test_clean_install.py tests/proof_context_engine/test_example_workflow.py
- Validation commands JSON: ["python -m pytest -q tests/proof_context_engine/test_clean_install.py tests/proof_context_engine/test_example_workflow.py"]
- Acceptance: PCCE-056 installs the built artifacts into clean offline-capable environments, runs imports/CLI/example, records hashes/SBOM, and reports optional unavailable profiles honestly.
- Gap task: Repair the smallest metadata, dependency, artifact, lock, SBOM, environment, example, or clean-install defect.

## PCCE-G600 F: frozen external generalization benchmark

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G500
- Dependencies JSON: ["PCCE-G500"]
- Fib priority: 21
- Priority: P1
- Track: benchmark
- Bundle: proof-context/epic-f
- Parallel lane: benchmark
- Resource class: evaluation-large
- Goal: Freeze a leakage-resistant three-class corpus, run configurations A-D, measure context/quality/routing/verification/assurance/economics, and evaluate predeclared thresholds.
- Producing tasks: PCCE-060, PCCE-061, PCCE-062, PCCE-063, PCCE-064, PCCE-065, PCCE-066, PCCE-067, PCCE-068, PCCE-079
- Evidence: artifacts/proof_carrying_context_engine/benchmark/epic_f_report.json
- Evidence requirements JSON: ["corpus manifest", "hidden-answer isolation", "A-D configuration manifests", "metric schemas", "pre-run threshold seal", "bounded self-hosting attempts and longitudinal disposition", "raw attempt records", "aggregate benchmark report"]
- Evidence criteria: At least typed structured, dynamic/plugin-heavy, and larger mature Python classes are revision-pinned; failed attempts and unavailable metrics remain visible; threshold misses lower qualification.
- Evidence source policy: Synthetic smoke, replay, or estimated provider/cost data cannot be labelled observed live-model quality or economics.
- Outputs: artifacts/proof_carrying_context_engine/benchmark/epic_f_report.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/benchmark/epic_f_report.json"]
- Validation: python -m pytest -q tests/proof_context_engine/benchmark
- Validation commands JSON: ["python -m pytest -q tests/proof_context_engine/benchmark"]
- Acceptance: PCCE-068 publishes all requested metrics, confidence/population/limitations, actual threshold outcomes, and no hidden expected patch leakage.
- Gap task: Close the smallest corpus, isolation, configuration, metric, execution, aggregation, or threshold-evaluation gap.

## PCCE-G700 G: security and trust-boundary hardening

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G500
- Dependencies JSON: ["PCCE-G500"]
- Fib priority: 34
- Priority: P0
- Track: security
- Bundle: proof-context/epic-g
- Parallel lane: security
- Resource class: security-large
- Goal: Threat-model and enforce repository, process, network, credential, adapter, patch, receipt, cache, benchmark, worktree, and interrupted-execution trust boundaries with adversarial E2E tests.
- Producing tasks: PCCE-070, PCCE-071, PCCE-072, PCCE-073, PCCE-074, PCCE-075, PCCE-076
- Evidence: artifacts/proof_carrying_context_engine/security/epic_g_gate.json
- Evidence requirements JSON: ["threat model", "sandbox enforcement receipt", "trust-store hardening", "patch/policy attacks", "prompt/leakage attacks", "concurrency/interruption attacks", "security gate"]
- Evidence criteria: Network is disabled by default, executables/providers are allowlisted, secrets are absent/redacted, filesystem and branch scope cannot escape, forged/stale/simulated evidence is rejected, and ambiguous partial effects fail closed.
- Evidence source policy: Policy configuration without enforcement and unit mocks without hostile end-to-end fixtures are insufficient.
- Outputs: artifacts/proof_carrying_context_engine/security/epic_g_gate.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/security/epic_g_gate.json"]
- Validation: python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/adversarial tests/proof_context_engine/security
- Validation commands JSON: ["python -m pytest -q external/ipfs_accelerate/test/proof_context_engine/adversarial tests/proof_context_engine/security"]
- Acceptance: PCCE-076 proves rejection of every required adversarial fixture and records residual risks; skipped or unavailable required security tests fail the gate.
- Gap task: Repair the smallest threat, sandbox, scope, forgery, replay, injection, leakage, concurrency, interruption, or compromised-adapter defect.

## PCCE-G800 H: release qualification and go/no-go

- Status: active
- Parent: PCCE-G000
- Parent goal IDs JSON: ["PCCE-G000"]
- Depends on: PCCE-G600, PCCE-G700
- Dependencies JSON: ["PCCE-G600", "PCCE-G700"]
- Fib priority: 55
- Priority: P0
- Track: release
- Bundle: proof-context/epic-h
- Parallel lane: release
- Resource class: release-coordinator
- Goal: Run current-head CI, assemble an immutable v0.1 release candidate, compute qualification, and issue explicit development/pilot/production go/no-go decisions.
- Producing tasks: PCCE-080, PCCE-081, PCCE-082, PCCE-083
- Evidence: artifacts/proof_carrying_context_engine/release/final_supervisor_report.json
- Evidence requirements JSON: ["required-fail CI", "release manifest and artifacts", "qualification calculation", "final board and decision report"]
- Evidence criteria: Required jobs cannot continue on error or report unavailable as passed; release artifacts bind source/locks/SBOM/schemas/vectors/corpus/results/limitations/rollback; the level follows evidence rather than component count.
- Evidence source policy: Historical CI, skipped required jobs, mutable dependencies, and task completion status alone cannot grant qualification.
- Outputs: artifacts/proof_carrying_context_engine/release/final_supervisor_report.json
- Predicted files JSON: ["artifacts/proof_carrying_context_engine/release/final_supervisor_report.json"]
- Validation: python -m pytest -q tests/proof_context_engine/release && python scripts/validate_proof_carrying_context_engine_board.py --check-all
- Validation commands JSON: ["python -m pytest -q tests/proof_context_engine/release", "python scripts/validate_proof_carrying_context_engine_board.py --check-all"]
- Acceptance: PCCE-083 lists all evidence and blockers, assigns at most the supported level, and explicitly recommends proceed, proceed with restrictions, or no-go for each requested deployment tier.
- Gap task: Repair the smallest CI, artifact, manifest, qualification, rollback, decision, or final-report gap.
