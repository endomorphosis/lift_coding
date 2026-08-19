# Formal Assurance Control Plane Objective Heap

Machine-ingestible goal and subgoal state for the `FACP-` program. The
executable projection is
`implementation_plan/docs/49-formal-assurance-control-plane.todo.md`.
Subgoals are ordinary goals with a `Parent` binding.

## Goal tree

```text
FACP-G000  Proof-carrying portfolio control plane
|-- FACP-G010  Source authority, inventory, TCB, and defect corpus
|-- FACP-G100  Formal Claim Algebra v1
|   |-- FACP-G110  Evidence semantics and Lean theorems
|   |-- FACP-G120  Executable kernel, bindings, and compatibility
|   `-- FACP-G130  Static ambiguous-claim enforcement
|-- FACP-G200  Four-path FCA production migration
|   |-- FACP-G210  Datasets import and outcome semantics
|   |-- FACP-G220  Accelerate capability, inference, and identity
|   |-- FACP-G230  Kit qualification and proof roles
|   `-- FACP-G240  SwissKnife browser/host boundary
|-- FACP-G300  Canonical contracts and effect admission
|   |-- FACP-G310  Canonical Contract Compiler
|   `-- FACP-G320  Effect Admission Kernel
|-- FACP-G400  Static and information-flow assurance
|   |-- FACP-G410  Import/effect/mock/outcome/CID analysis and repair
|   `-- FACP-G420  Noninterference and declassification
|-- FACP-G500  Transactional and backend assurance
|   |-- FACP-G510  Transactional Effect Protocols
|   `-- FACP-G520  Backend Certification Synthesizer
|-- FACP-G600  Incremental and compositional verification
|   |-- FACP-G610  Semantic dependency and invalidation
|   |-- FACP-G620  Assume-guarantee contracts
|   |-- FACP-G630  Translation validation
|   `-- FACP-G640  Proof and solver orchestration
|-- FACP-G700  Bounded synthesis
|   |-- FACP-G710  Counterexample-guided repair
|   `-- FACP-G720  Reactive supervisor control
`-- FACP-G800  Proof-carrying qualification and release
    |-- FACP-G810  Supply-chain, rights, documentation, and conformance
    `-- FACP-G820  End-to-end composed release
```

## FACP-G000 Proof-carrying portfolio control plane

- Status: active
- Parent:
- Parent goal IDs JSON: []
- Depends on:
- Dependencies JSON: []
- Priority: P0
- Track: program-control
- Goal: Make invalid claims, unauthorized effects, false success, stale proof reuse, incompatible contracts, mutable releases, and browser-authored authority unrepresentable or mechanically rejected across the portfolio.
- Producing tasks: FACP-000, FACP-020, FACP-031, FACP-037, FACP-041, FACP-046, FACP-054, FACP-060
- Evidence: facp/control-plane@1, facp/formal-claim-algebra-v1@1, facp/terminal-release@1
- Outputs: implementation_plan/docs/49-formal-assurance-control-plane-plan-2026-08-19.md, implementation_plan/docs/49-formal-assurance-control-plane.objectives.md, implementation_plan/docs/49-formal-assurance-control-plane.todo.md
- Validation: python3 scripts/validate_formal_assurance_control_plane_board.py --check-all
- Acceptance: Every child goal has current typed evidence; all zero safety floors hold; a composed portfolio release independently verifies against the exact source forest, dependency lock, policies, rights, and live capability receipts.
- Conflict policy: Control artifacts are protected; only supervisor lifecycle code changes task status.

## FACP-G010 Source authority, inventory, TCB, and defect corpus

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on:
- Dependencies JSON: []
- Priority: P0
- Track: source-inventory
- Goal: Freeze exact source authority, reconcile reusable implementations, inventory unsafe promotions and release defects, and build the seeded counterexample corpus before new kernel code.
- Producing tasks: FACP-001, FACP-002, FACP-003, FACP-004, FACP-005, FACP-006, FACP-007, FACP-008
- Evidence: facp/source-binding@1, facp/claim-inventory@1, facp/defect-corpus@1, facp/tcb@1
- Outputs: implementation_plan/formal_assurance_control_plane/baseline
- Validation: python3 -m pytest test/formal_assurance -q
- Acceptance: Inventories bind exact commits/gitlinks and source spans, distinguish existing compatible components from semantic conflicts, and cover every seeded defect without treating discovery as completion.
- Conflict policy: Initial inventory tasks own separate reports and tests and may run concurrently; FACP-008 is the sole fan-in.

## FACP-G100 Formal Claim Algebra v1

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G010
- Dependencies JSON: ["FACP-G010"]
- Priority: P0
- Track: formal-claims
- Goal: Define, prove, execute, and enforce the multidimensional evidence algebra that becomes the only production promotion authority.
- Producing tasks: FACP-009, FACP-010, FACP-011, FACP-012, FACP-013, FACP-014, FACP-015, FACP-016, FACP-017, FACP-018, FACP-019, FACP-020
- Evidence: facp/fca-spec@1, facp/fca-lean-theorem@1, facp/fca-kernel@1, facp/fca-conformance@1
- Outputs: Mcp-Plus-Plus/docs/spec/formal-claim-algebra-v1.md, Mcp-Plus-Plus/schemas/assurance/v1, Mcp-Plus-Plus/formal/lean
- Validation: python3 -m pytest test/formal_assurance/test_facp_020_fca_gate.py -q
- Acceptance: Fixture, simulation, unchecked hash, browser policy, expired delegation, stale receipt, and unknown external outcome cannot construct a live authorized observed current success claim in Lean, Rust, Python, or TypeScript.
- Conflict policy: MCP++ owns normative semantics; repository adapters cannot broaden them.

## FACP-G110 Evidence semantics and Lean theorems

- Status: active
- Parent: FACP-G100
- Parent goal IDs JSON: ["FACP-G100"]
- Depends on: FACP-G010
- Dependencies JSON: ["FACP-G010"]
- Priority: P0
- Track: formal-claims-proof
- Goal: Specify the evidence product, legal transitions, promotion predicates, and prove the illegal-promotion theorem suite.
- Producing tasks: FACP-009, FACP-010, FACP-011, FACP-012
- Evidence: facp/evidence-product@1, facp/promotion-predicates@1, facp/illegal-promotion-proof@1
- Outputs: Mcp-Plus-Plus/docs/spec/formal-claim-algebra-v1.md, Mcp-Plus-Plus/formal/lean/FormalClaimAlgebra
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_proof.py -q
- Acceptance: Definitions are closed and decidable; theorem statements cover every forbidden origin and cross-dimensional non-implication; proof checking has no admitted axioms beyond the reviewed TCB.
- Conflict policy: Lean and normative specification files are owned only by this lane.

## FACP-G120 Executable kernel, bindings, and compatibility

- Status: active
- Parent: FACP-G100
- Parent goal IDs JSON: ["FACP-G100"]
- Depends on: FACP-G110
- Dependencies JSON: ["FACP-G110"]
- Priority: P0
- Track: formal-claims-runtime
- Goal: Implement closed Rust transitions, generate Python/TypeScript projections, and conservatively adapt existing supervisor and Kit assurance records.
- Producing tasks: FACP-013, FACP-014, FACP-015, FACP-016, FACP-017, FACP-018
- Evidence: facp/fca-rust@1, facp/fca-python@1, facp/fca-typescript@1, facp/compatibility-adapters@1
- Outputs: Mcp-Plus-Plus/tests-rs/src/formal_claim_algebra.rs, Mcp-Plus-Plus/tests-py/validators/formal_claim_algebra.py, Mcp-Plus-Plus/tests-ts/src/formalClaimAlgebra.ts
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_vectors.py -q
- Acceptance: All projections accept and reject identical transitions; legacy total ladders map conservatively and cannot acquire evidence dimensions they did not carry.
- Conflict policy: Fan-out implementations own separate language files; compatibility adapters own separate repository modules.

## FACP-G130 Static ambiguous-claim enforcement

- Status: active
- Parent: FACP-G100
- Parent goal IDs JSON: ["FACP-G100"]
- Depends on: FACP-G110
- Dependencies JSON: ["FACP-G110"]
- Priority: P0
- Track: claim-scanner
- Goal: Reject new unqualified success, support, availability, verification, proof, currentness, and production fields and provide actionable traces.
- Producing tasks: FACP-019, FACP-020
- Evidence: facp/ambiguous-claim-scan@1, facp/fca-conformance@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_claim_scanner.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_scanner.py -q
- Acceptance: The scanner detects the seeded corpus, preserves explicit typed compatibility fields, and blocks novel ambiguous production APIs with source spans and repair guidance.
- Conflict policy: Scanner code is isolated from migration adapters; FACP-020 only consumes reports.

## FACP-G200 Four-path FCA production migration

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: fca-migration
- Goal: Apply FCA to the required Accelerate, Datasets, Kit, and SwissKnife paths and close the day-90 safety gate.
- Producing tasks: FACP-021, FACP-022, FACP-023, FACP-024, FACP-025, FACP-026, FACP-027, FACP-028, FACP-029, FACP-030, FACP-031
- Evidence: facp/datasets-migration@1, facp/accelerate-migration@1, facp/kit-migration@1, facp/swissknife-migration@1, facp/day90-gate@1
- Outputs: implementation_plan/formal_assurance_control_plane/gates/day90.json
- Validation: python3 -m pytest test/formal_assurance/test_facp_031_four_path_gate.py -q
- Acceptance: Migrated paths have no browser authority, import mutation, false success, pseudo-CID, mock promotion, or hermetic-to-live promotion; compatibility APIs return typed evidence.
- Conflict policy: Four repositories migrate in parallel; FACP-031 is the sole cross-repository fan-in.

## FACP-G210 Datasets import and outcome semantics

- Status: active
- Parent: FACP-G200
- Parent goal IDs JSON: ["FACP-G200"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: datasets-migration
- Goal: Make core imports hermetic, initialization explicit, and download/upload/semantic outcomes evidence-qualified.
- Producing tasks: FACP-021, FACP-022, FACP-023
- Evidence: facp/datasets-import-purity@1, facp/datasets-outcomes@1
- Outputs: external/ipfs_datasets/ipfs_datasets_py/assurance
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/test_formal_assurance_import_and_outcomes.py -q
- Acceptance: Cold core import has no install/network/process/persistent-write/environment mutation; missing effects return typed Unavailable or Failed rather than success.
- Conflict policy: Datasets lane exclusively owns new assurance adapter and dedicated tests; package-root fan-in occurs in FACP-022.

## FACP-G220 Accelerate capability, inference, and identity

- Status: active
- Parent: FACP-G200
- Parent goal IDs JSON: ["FACP-G200"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: accelerate-migration
- Goal: Isolate simulation, require probe evidence, replace mock inference success, and remove pseudo-CID construction.
- Producing tasks: FACP-024, FACP-025, FACP-026
- Evidence: facp/accelerate-mock-flow@1, facp/accelerate-outcomes@1, facp/canonical-cid@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/assurance
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_formal_assurance_accelerate_migration.py -q
- Acceptance: No mock-origin value reaches production capability or inference success; supported paths recompute canonical content identity and reject hash-shaped strings.
- Conflict policy: Migration uses new adapters and dedicated tests; legacy paths are isolated, not silently relabeled.

## FACP-G230 Kit qualification and proof roles

- Status: active
- Parent: FACP-G200
- Parent goal IDs JSON: ["FACP-G200"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: kit-migration
- Goal: Adapt and enforce Kit's honest hermetic/conditional/live and candidate/admitted/current semantics through FCA.
- Producing tasks: FACP-027, FACP-028
- Evidence: facp/kit-live-gate@1, facp/kit-proof-role-gate@1
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_kit_adapter.py -q
- Acceptance: Backend selection requires current live evidence; stale or ambiguous proof execution cannot update current; zero-qualified backend remains a valid honest state.
- Conflict policy: Existing proof-store and support-matrix semantics are preserved; the adapter cannot weaken them.

## FACP-G240 SwissKnife browser/host boundary

- Status: active
- Parent: FACP-G200
- Parent goal IDs JSON: ["FACP-G200"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: swissknife-migration
- Goal: Prove browser nonauthority and consume host-issued, exact-argument-bound admission outcomes.
- Producing tasks: FACP-029, FACP-030
- Evidence: facp/browser-nonauthority@1, facp/host-admission-projection@1
- Outputs: swissknife/src/services/mcp/formalAssuranceGateway.ts
- Validation: python3 -m pytest test/formal_assurance/test_facp_030_swissknife_host_projection.py -q
- Acceptance: Browser allow/deny, consent, tenant, and dry-run changes cannot grant authority; default granted consent is absent; the UI displays the exact argument digest and host decision.
- Conflict policy: SwissKnife owns presentation and request projection only; host policy is not duplicated in TypeScript.

## FACP-G300 Canonical contracts and effect admission

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G100, FACP-G200
- Dependencies JSON: ["FACP-G100", "FACP-G200"]
- Priority: P0
- Track: contracts-admission
- Goal: Generate one canonical contract family and require common authenticated admission for all migrated effects.
- Producing tasks: FACP-032, FACP-033, FACP-034, FACP-035, FACP-036, FACP-037, FACP-038, FACP-039, FACP-040, FACP-041
- Evidence: facp/contract-conformance@1, facp/effect-admission@1
- Outputs: Mcp-Plus-Plus/schemas/assurance/v1, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission
- Validation: python3 -m pytest test/formal_assurance/test_facp_041_effect_admission_gate.py -q
- Acceptance: Canonical bytes/CIDs agree across languages and no migrated effectful handler is callable without a current argument-bound AdmissionToken.
- Conflict policy: Contract generation precedes runtime integration; one fan-in task owns each shared registry.

## FACP-G310 Canonical Contract Compiler

- Status: active
- Parent: FACP-G300
- Parent goal IDs JSON: ["FACP-G300"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: canonical-contracts
- Goal: Compile Assurance IDL into strict schemas, codecs, bindings, errors, vectors, documentation, and formal skeletons.
- Producing tasks: FACP-032, FACP-033, FACP-034, FACP-035, FACP-036, FACP-037
- Evidence: facp/operation-spec@1, facp/dag-cbor-profile@1, facp/translation-validation@1
- Outputs: Mcp-Plus-Plus/tools/assurance_idl, Mcp-Plus-Plus/schemas/assurance/v1
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_contract_compiler.py -q
- Acceptance: EvidenceEnvelope, OperationSpec, AdmissionToken, and EffectReceipt generate deterministic strict projections and identical canonical identity in Rust, Python, TypeScript, and Go.
- Conflict policy: Generated files have one compiler owner and must not be hand-edited.

## FACP-G320 Effect Admission Kernel

- Status: active
- Parent: FACP-G300
- Parent goal IDs JSON: ["FACP-G300"]
- Depends on: FACP-G200, FACP-G310
- Dependencies JSON: ["FACP-G200", "FACP-G310"]
- Priority: P0
- Track: effect-admission
- Goal: Enforce closed effect classes, typestate, authenticated delegation, conservative policy, one-use confirmation, lease, revocation, and observation obligations.
- Producing tasks: FACP-038, FACP-039, FACP-040, FACP-041
- Evidence: facp/effect-typestate@1, facp/admission-kernel@1, facp/common-transport-gate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_admission_kernel.py -q
- Acceptance: Browser, prompt, model, peer, payment, and caller-selected tenant inputs cannot construct a token; revocation and changed arguments fail; all migrated transports consume the same decision.
- Conflict policy: The host kernel is the only token constructor; transport adapters are consumers.

## FACP-G400 Static and information-flow assurance

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G100, FACP-G300
- Dependencies JSON: ["FACP-G100", "FACP-G300"]
- Priority: P0
- Track: static-assurance
- Goal: Infer effects/trust/outcomes/identity, synthesize bounded repairs, and prove critical information-flow boundaries.
- Producing tasks: FACP-042, FACP-043, FACP-044
- Evidence: facp/ipa@1, facp/deterministic-repairs@1, facp/noninterference@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_static.py -q
- Acceptance: Seeded import, mock, false-success, CID, secret, tenant, and browser-authority flows are found with bounded traces; repairs do not expand scope; two-run tests pass.
- Conflict policy: Static facts, repairs, and hyperproperty tests own separate modules.

## FACP-G410 Import/effect/mock/outcome/CID analysis and repair

- Status: active
- Parent: FACP-G400
- Parent goal IDs JSON: ["FACP-G400"]
- Depends on: FACP-G100
- Dependencies JSON: ["FACP-G100"]
- Priority: P0
- Track: abstract-interpretation
- Goal: Extend existing AST/provenance infrastructure with product abstract domains, Datalog rules, CEGAR refinement, dynamic import sandboxing, and fixed repair grammars.
- Producing tasks: FACP-042, FACP-043
- Evidence: facp/ipa-analysis@1, facp/ipa-repair@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipa_formal_assurance.py -q
- Acceptance: Every violation includes source span and trace; core import checks are network/install free; false positives can refine without weakening seeded defects.
- Conflict policy: Reuse existing indexes and graphs through adapters; do not build a parallel repository scanner.

## FACP-G420 Noninterference and declassification

- Status: active
- Parent: FACP-G400
- Parent goal IDs JSON: ["FACP-G400"]
- Depends on: FACP-G320, FACP-G410
- Dependencies JSON: ["FACP-G320", "FACP-G410"]
- Priority: P0
- Track: information-flow
- Goal: Label secrets and private data, require explicit declassification, and check browser/host, tenant, prompt/authority, credential, and witness hyperproperties.
- Producing tasks: FACP-044
- Evidence: facp/information-flow@1, facp/two-run-noninterference@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/information_flow_assurance.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_information_flow_assurance.py -q
- Acceptance: Public evidence contains no secret/host-path/private-witness value; cross-tenant and browser-nonauthority two-run suites pass; every declassification is policy/actor/destination/source bound.
- Conflict policy: Labels are shared contracts; declassification sites remain repository-owned.

## FACP-G500 Transactional and backend assurance

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G300, FACP-G400
- Dependencies JSON: ["FACP-G300", "FACP-G400"]
- Priority: P0
- Track: protocol-backend
- Goal: Model and monitor crash/retry/concurrency protocols and certify only backends with current live evidence.
- Producing tasks: FACP-045, FACP-046, FACP-053, FACP-054
- Evidence: facp/transaction-models@1, facp/runtime-monitor@1, facp/backend-certification@1
- Outputs: Mcp-Plus-Plus/formal/protocols, external/ipfs_kit/ipfs_kit_py/assurance/backend_certification.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_054_backend_cohort.py -q
- Acceptance: Required invariants survive bounded models and crash injection; configured/hermetic evidence cannot select a live backend; cohort receipts are current or explicitly nonqualified.
- Conflict policy: MCP++ owns models, Accelerate owns runtime monitor, Kit owns certification receipts.

## FACP-G510 Transactional Effect Protocols

- Status: active
- Parent: FACP-G500
- Parent goal IDs JSON: ["FACP-G500"]
- Depends on: FACP-G320
- Dependencies JSON: ["FACP-G320"]
- Priority: P0
- Track: transactional-protocols
- Goal: Specify admission, effect, proof promotion, current pointer, lease, retry, crash, compensation, and unknown-outcome behavior and enforce trace conformance.
- Producing tasks: FACP-045, FACP-046
- Evidence: facp/tep-models@1, facp/tep-monitor@1
- Outputs: Mcp-Plus-Plus/formal/protocols/transactional_effects, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_transition_monitor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transition_monitor.py -q
- Acceptance: NoDoubleEffect, NoStaleFenceCompletion, NoSuccessWithoutObservation, NoConfirmationReuse, and NoReplayOfUnknownIrreversibleEffect hold for the declared bounds and runtime vectors.
- Conflict policy: Model and monitor implementations are file-disjoint; FACP-046 owns trace-vector fan-in.

## FACP-G520 Backend Certification Synthesizer

- Status: active
- Parent: FACP-G500
- Parent goal IDs JSON: ["FACP-G500"]
- Depends on: FACP-G510, FACP-G310
- Dependencies JSON: ["FACP-G510", "FACP-G310"]
- Priority: P1
- Track: backend-certification
- Goal: Generate and execute certification for local filesystem, pinned IPFS, and Iroh without promoting registration or configuration.
- Producing tasks: FACP-053, FACP-054
- Evidence: facp/backend-suite@1, facp/backend-cohort@1
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance/backend_certification.py, external/ipfs_kit/data/formal_assurance/backend_receipts
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_backend_certification.py -q
- Acceptance: Generated suites cover write/read-back/digest/delete/replay/timeout/concurrency/restart/corruption/large objects/credentials/parity; only a current live admitted receipt promotes support.
- Conflict policy: Certification writes immutable receipts and a generated matrix; it does not edit backend implementations.

## FACP-G600 Incremental and compositional verification

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G100, FACP-G300, FACP-G500
- Dependencies JSON: ["FACP-G100", "FACP-G300", "FACP-G500"]
- Priority: P1
- Track: incremental-composition
- Goal: Make change impact, proof reuse, repository contracts, translations, and solver escalation source-bound and explainable.
- Producing tasks: FACP-047, FACP-048, FACP-049, FACP-050
- Evidence: facp/semantic-capsules@1, facp/assume-guarantee@1, facp/translation-receipts@1, facp/proof-orchestration@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_capsule.py, external/ipfs_datasets/ipfs_datasets_py/logic/translation_validation
- Validation: python3 -m pytest test/formal_assurance/test_facp_050_incremental_composition.py -q
- Acceptance: Mutation corpus has zero missed required validations; repository boundary failures are named; lossy translations name loss; proof reuse explains its unchanged or proved-equivalent closure.
- Conflict policy: Capsules, repository contracts, translation receipts, and solver orchestration own distinct paths.

## FACP-G610 Semantic dependency and invalidation

- Status: active
- Parent: FACP-G600
- Parent goal IDs JSON: ["FACP-G600"]
- Depends on: FACP-G100, FACP-G410
- Dependencies JSON: ["FACP-G100", "FACP-G410"]
- Priority: P1
- Track: semantic-invalidation
- Goal: Extend existing dependency/provenance graphs into content-addressed semantic capsules with sound incremental invalidation and minimal explanations.
- Producing tasks: FACP-047
- Evidence: facp/semantic-capsule@1, facp/invalidation-soundness@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_capsule.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_semantic_capsule.py -q
- Acceptance: Source, contracts, effects, policies, proofs, tests, environments, and releases participate in invalidation; stale receipts demote automatically; raw source is fetched only on capsule demand.
- Conflict policy: Extend current semantic dependency graph rather than duplicating it.

## FACP-G620 Assume-guarantee contracts

- Status: active
- Parent: FACP-G600
- Parent goal IDs JSON: ["FACP-G600"]
- Depends on: FACP-G510, FACP-G610
- Dependencies JSON: ["FACP-G510", "FACP-G610"]
- Priority: P1
- Track: assume-guarantee
- Goal: Publish and compose finite versioned assumptions and guarantees for each repository.
- Producing tasks: FACP-048
- Evidence: facp/repository-contracts@1, facp/composition-boundaries@1
- Outputs: Mcp-Plus-Plus/schemas/assurance/v1/repository-contracts.json
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assume_guarantee_contracts.py -q
- Acceptance: Every assumption is discharged by a qualified component or remains explicit; integration failures identify the violated boundary; contract changes invalidate consumers.
- Conflict policy: MCP++ owns the normative records; repositories supply evidence, not rewritten copies.

## FACP-G630 Translation validation

- Status: active
- Parent: FACP-G600
- Parent goal IDs JSON: ["FACP-G600"]
- Depends on: FACP-G310, FACP-G610
- Dependencies JSON: ["FACP-G310", "FACP-G610"]
- Priority: P1
- Track: translation-validation
- Goal: Emit translation receipts, define safety refinement, validate round trips, and admit only proved or solver-validated normalization rewrites.
- Producing tasks: FACP-049
- Evidence: facp/translation-receipt@1, facp/deontic-refinement@1, facp/rewrite-trust@1
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/translation_validation/formal_assurance.py
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/logic/test_formal_assurance_translation_validation.py -q
- Acceptance: Prohibitions never broaden to permission, obligations remain or strengthen, unsupported constructs name loss, and adversarial negation/exception/time/conflict/jurisdiction cases have explicit dispositions.
- Conflict policy: Reuse Datasets semantic API and e-graph facilities; no second compiler API.

## FACP-G640 Proof and solver orchestration

- Status: active
- Parent: FACP-G600
- Parent goal IDs JSON: ["FACP-G600"]
- Depends on: FACP-G610, FACP-G630
- Dependencies JSON: ["FACP-G610", "FACP-G630"]
- Priority: P1
- Track: proof-orchestration
- Goal: Route obligations through the cheapest sound method, bind incremental caches to capsules, reconstruct candidates, and explain escalation/conflict.
- Producing tasks: FACP-050
- Evidence: facp/proof-router@1, facp/proof-cache-key@1, facp/solver-conflict@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/formal_assurance_orchestrator.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_orchestrator.py -q
- Acceptance: Every result names assumptions/verifier/toolchain; unknown never becomes verified; cache reuse has a derivation; disagreement creates a conflict record; proof/LLM cost is measured.
- Conflict policy: Compose existing proof caches and routers through one adapter; do not fork solver authority.

## FACP-G700 Bounded synthesis

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G400, FACP-G500, FACP-G600
- Dependencies JSON: ["FACP-G400", "FACP-G500", "FACP-G600"]
- Priority: P1
- Track: bounded-synthesis
- Goal: Admit only grammar-bounded proof-carrying patches and hard-property-preserving supervisor controllers.
- Producing tasks: FACP-051, FACP-052
- Evidence: facp/cegis-repair@1, facp/reactive-controller@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_assurance_controller.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_synthesis.py -q
- Acceptance: Repairs cannot escape grammar or waive obligations; controllers never weaken hard properties and produce unrealizable cores; LLM output remains proposal-only.
- Conflict policy: Repair and controller synthesis own separate modules and share only generated contracts.

## FACP-G710 Counterexample-guided repair

- Status: active
- Parent: FACP-G700
- Parent goal IDs JSON: ["FACP-G700"]
- Depends on: FACP-G410, FACP-G510, FACP-G610, FACP-G640
- Dependencies JSON: ["FACP-G410", "FACP-G510", "FACP-G610", "FACP-G640"]
- Priority: P1
- Track: cegis-repair
- Goal: Repair recurring defect classes through approved grammars, fast abstract checks, solver/model validation, affected tests/proofs, and PatchCertificate.
- Producing tasks: FACP-051
- Evidence: facp/repair-grammar@1, facp/patch-certificate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_cegis.py -q
- Acceptance: Seeded false-success, mock, CID, lease, browser, mutable dependency, stale proof, import, license, and recovery defects are eliminated without new counterexamples; scope escape is rejected.
- Conflict policy: The LLM can choose a grammar or sketch only; deterministic admission owns edits and completion.

## FACP-G720 Reactive supervisor control

- Status: active
- Parent: FACP-G700
- Parent goal IDs JSON: ["FACP-G700"]
- Depends on: FACP-G320, FACP-G510, FACP-G620, FACP-G640
- Dependencies JSON: ["FACP-G320", "FACP-G510", "FACP-G620", "FACP-G640"]
- Priority: P1
- Track: reactive-control
- Goal: Synthesize or independently validate bounded provider, retry, lease, human-gate, proof-escalation, compensation, and shutdown policies.
- Producing tasks: FACP-052
- Evidence: facp/supervisor-controller@1, facp/unrealizable-core@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_assurance_controller.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_controller.py -q
- Acceptance: Hard safety properties hold, retry budgets are bounded, fallback cannot change authority/evidence class, and healthy dependencies permit terminal progress.
- Conflict policy: Controller synthesis targets control policy only, never arbitrary repository source.

## FACP-G800 Proof-carrying qualification and release

- Status: active
- Parent: FACP-G000
- Parent goal IDs JSON: ["FACP-G000"]
- Depends on: FACP-G500, FACP-G600, FACP-G700
- Dependencies JSON: ["FACP-G500", "FACP-G600", "FACP-G700"]
- Priority: P0
- Track: release
- Goal: Qualify exact immutable source, dependencies, rights, builds, claims, conformance, capabilities, and one composed workflow into an independently verifiable release.
- Producing tasks: FACP-055, FACP-056, FACP-057, FACP-058, FACP-059, FACP-060
- Evidence: facp/release-predicate@1, facp/reproducible-build@1, facp/rights@1, facp/composed-workflow@1, facp/terminal-release@1
- Outputs: implementation_plan/formal_assurance_control_plane/release
- Validation: python3 -m pytest test/formal_assurance/test_facp_060_terminal_release.py -q
- Acceptance: Release is exact-tree, immutable, rights-resolved or human-blocked, reproducible, signed, current, live-capability honest, and independently verified with all zero floors.
- Conflict policy: Qualification consumes immutable evidence; only the terminal fan-in writes the release manifest.

## FACP-G810 Supply-chain, rights, documentation, and conformance

- Status: active
- Parent: FACP-G800
- Parent goal IDs JSON: ["FACP-G800"]
- Depends on: FACP-G520, FACP-G600
- Dependencies JSON: ["FACP-G520", "FACP-G600"]
- Priority: P0
- Track: release-qualification
- Goal: Define release/rights predicates, immutable locks, reproducible provenance, evidence-checked documentation, and external cross-language conformance.
- Producing tasks: FACP-055, FACP-056, FACP-057, FACP-058
- Evidence: facp/supply-chain@1, facp/rights-ir@1, facp/docs-claims@1, facp/external-conformance@1
- Outputs: implementation_plan/formal_assurance_control_plane/release/qualification
- Validation: python3 -m pytest test/formal_assurance/test_facp_058_release_qualification.py -q
- Acceptance: Mutable dependencies and stale receipts block; SPDX/rights ambiguity remains explicit; documentation claims narrow automatically; an independent implementation passes vectors.
- Conflict policy: Locks, rights, docs, and external conformance own distinct artifacts.

## FACP-G820 End-to-end composed release

- Status: active
- Parent: FACP-G800
- Parent goal IDs JSON: ["FACP-G800"]
- Depends on: FACP-G710, FACP-G720, FACP-G810
- Dependencies JSON: ["FACP-G710", "FACP-G720", "FACP-G810"]
- Priority: P0
- Track: terminal-release
- Goal: Compose and independently qualify one SwissKnife-to-host-to-Datasets-to-Accelerate-to-Kit-to-SwissKnife workflow.
- Producing tasks: FACP-059, FACP-060
- Evidence: facp/composition-proof@1, facp/terminal-release@1
- Outputs: implementation_plan/formal_assurance_control_plane/release/terminal
- Validation: python3 -m pytest test/formal_assurance/test_facp_060_terminal_release.py -q
- Acceptance: Every repository guarantee holds under discharged assumptions; authority/effect/evidence transitions conform; release binds exact forest, policies, proofs, tests, live capabilities, rights, artifacts, and residual risks.
- Conflict policy: FACP-059 produces the demo evidence; FACP-060 alone seals the terminal manifest.
