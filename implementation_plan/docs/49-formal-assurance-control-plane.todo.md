# Formal Assurance Control Plane Taskboard

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix
`FACP-`. Subgoal bindings are carried in `Goal id`. All implementation
providers are proposal-only; completion requires the declared validation and
evidence. Objective/codebase refill is disabled for this reviewed board.

## Parallel waves

```text
W0  FACP-000 (completed control seal)
W1  FACP-001 | 002 | 003 | 004 | 005 | 006 | 007
W2  FACP-008
W3  FCA semantics, theorem, executable kernel, language adapters, scanner
W4  Accelerate | Datasets | Kit | SwissKnife migrations
W5  canonical contracts | effect admission | static assurance
W6  transactional protocols | semantic capsules | repository contracts
W7  translation/proof orchestration | bounded synthesis | backend certification
W8  supply chain | rights | documentation | external conformance
W9  composed workflow -> terminal release
```

Tasks may run concurrently only when their dependency, predicted-file,
resource, lease, and merge projections permit it. `Parallel lane` is a hint,
not authority.

## FACP-000 Seal the formal-assurance control program

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: program-control
- Depends on:
- Goal id: FACP-G000
- Owning repository: root
- Outputs: implementation_plan/docs/49-formal-assurance-control-plane-plan-2026-08-19.md, implementation_plan/docs/49-formal-assurance-control-plane.objectives.md, implementation_plan/docs/49-formal-assurance-control-plane.todo.md, config/formal_assurance_control_plane_scheduler.json, scripts/validate_formal_assurance_control_plane_board.py, scripts/formal_assurance_control_plane_supervisor.sh
- Predicted files: implementation_plan/docs/49-formal-assurance-control-plane-plan-2026-08-19.md, implementation_plan/docs/49-formal-assurance-control-plane.objectives.md, implementation_plan/docs/49-formal-assurance-control-plane.todo.md, config/formal_assurance_control_plane_scheduler.json, scripts/validate_formal_assurance_control_plane_board.py, scripts/formal_assurance_control_plane_supervisor.sh
- Validation: python3 -m scripts.validate_formal_assurance_control_plane_board --check-all
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/control
- Parallel lane: facp-control
- Resource class: cpu-small
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: write the six protected control artifacts before launch; create a dedicated Git branch/worktree; start only after clean preflight
- Prohibited effects: edit unrelated dirty state; infer completion from prose; mutate repository code
- Conflict policy: These paths are protected after this task and may be changed only by reviewed plan steering.
- Preconditions: Dedicated branch and exact clean submodule gitlinks are available.
- Evidence subset: parseable goals/subgoals/tasks, acyclic DAG, ready width, source binding, sealed scheduler, launch-health contract
- Acceptance: Validator reports valid; initial ready tasks are FACP-001 through FACP-007; scheduler preflight binds exact clean source and four strict lanes; no implementation claim is pre-completed.

## FACP-001 Inventory reusable formal and supervisor primitives

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading external/ipfs_accelerate
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/reusable_primitives.json, test/formal_assurance/test_facp_001_reusable_primitives.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/reusable_primitives.json, test/formal_assurance/test_facp_001_reusable_primitives.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_001_reusable_primitives.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/reuse
- Parallel lane: facp-inventory-1
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: read exact tracked source; write only declared report and test
- Prohibited effects: edit implementation code; mark discovered artifacts authoritative; install tools
- Conflict policy: Own only the reusable-primitives report and test; do not edit any repository being inspected.
- Preconditions: FACP-000 control seal is committed.
- Evidence subset: existing evidence ladders, proof contracts/caches, planners, dependency graphs, authorization, repair, lease/fence/recovery, runtime monitors
- Acceptance: Every reusable component has exact commit/path/symbol, semantic authority, gaps, adoption disposition, and compatibility risk; total assurance ladders are flagged for conservative FCA adaptation rather than duplication.

## FACP-002 Inventory Accelerate unsafe claims and promotions

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading external/ipfs_accelerate
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/accelerate_claims.json, test/formal_assurance/test_facp_002_accelerate_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/accelerate_claims.json, test/formal_assurance/test_facp_002_accelerate_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_002_accelerate_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/accelerate
- Parallel lane: facp-inventory-2
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: read exact Accelerate source and tests; write declared report/test
- Prohibited effects: execute providers; edit Accelerate; promote mocks or runtime observations
- Conflict policy: Own only the Accelerate inventory artifacts.
- Preconditions: Exact accelerator gitlink is clean.
- Evidence subset: mock worker/hardware/handler flows, inference outcomes, raw hashes, pseudo-CIDs, fallback namespaces, success/support fields
- Acceptance: Report includes source spans, call/flow path, production reachability, current tests, counterexample seed, and proposed FCA/IPA repair class for every confirmed defect.

## FACP-003 Inventory Datasets import, outcome, and rights defects

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading external/ipfs_datasets
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/datasets_claims.json, test/formal_assurance/test_facp_003_datasets_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/datasets_claims.json, test/formal_assurance/test_facp_003_datasets_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_003_datasets_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/datasets
- Parallel lane: facp-inventory-3
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: static reads and a network/process/write-denied cold-import probe; write declared report/test
- Prohibited effects: package installation; network; source mutation; legal compatibility conclusion
- Conflict policy: Own only the Datasets inventory artifacts.
- Preconditions: Exact Datasets gitlink is clean; auto-install environment is disabled.
- Evidence subset: module-top-level effects, installer reachability, PATH/environment writes, download/upload fallbacks, semantic results, MIT/AGPL declarations
- Acceptance: Import/effect traces and false-success spans are reproducible; rights conflict is encoded as unresolved human legal review rather than inferred compatibility.

## FACP-004 Inventory Kit evidence, backend, and proof-role semantics

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading external/ipfs_kit
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/kit_evidence.json, test/formal_assurance/test_facp_004_kit_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/kit_evidence.json, test/formal_assurance/test_facp_004_kit_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_004_kit_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/kit
- Parallel lane: facp-inventory-0
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: read exact Kit source, matrices, tests, and receipts; write declared report/test
- Prohibited effects: run live backends; edit Kit; relabel hermetic evidence as live
- Conflict policy: Own only the Kit inventory artifacts.
- Preconditions: Exact Kit gitlink is clean.
- Evidence subset: hermetic/conditional/live support, configured/selected states, candidate/admitted/current proof roles, CAS/WAL/recovery, receipt freshness
- Acceptance: Report preserves Kit's honest distinctions, identifies exact adapter seams, records zero live-qualified backends when supported by current evidence, and does not propose a weaker replacement.

## FACP-005 Inventory SwissKnife authority and information flows

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading swissknife
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/swissknife_authority.json, test/formal_assurance/test_facp_005_swissknife_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/swissknife_authority.json, test/formal_assurance/test_facp_005_swissknife_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_005_swissknife_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/swissknife
- Parallel lane: facp-inventory-1
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: read exact SwissKnife source and tests; write declared report/test
- Prohibited effects: browser/network execution; source mutation; infer license rights
- Conflict policy: Own only the SwissKnife inventory artifacts.
- Preconditions: Exact SwissKnife gitlink is clean.
- Evidence subset: browser policy/consent defaults, tenant selection, dry-run/live projection, host dispatch, secrets/paths/logs/prompts, license/provenance
- Acceptance: Every browser-to-host authority and sensitive-flow edge has a source span, owner, trust label, negative test seed, and removal/adaptation target; missing rights remain explicit.

## FACP-006 Inventory MCP++ schemas and canonicalization

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root, reading Mcp-Plus-Plus
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/mcplusplus_contracts.json, test/formal_assurance/test_facp_006_mcplusplus_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/mcplusplus_contracts.json, test/formal_assurance/test_facp_006_mcplusplus_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_006_mcplusplus_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/mcplusplus
- Parallel lane: facp-inventory-2
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: read exact schemas/specs/vectors/validators; write declared report/test
- Prohibited effects: mutate normative specs; select a format without evidence; call providers
- Conflict policy: Own only the MCP++ inventory artifacts.
- Preconditions: Exact MCP++ gitlink is clean.
- Evidence subset: IDL, profiles A-H, DAG-JSON/DAG-CBOR/JSON choices, CID families, Python/TS/Rust/Go validators, duplicate semantics, unknown-field behavior
- Acceptance: Report maps every wire model and canonicalization rule across languages, identifies conflicting/permissive choices, and names the smallest compiler source of truth.

## FACP-007 Inventory release, dependency, Git, and rights qualification

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-000
- Goal id: FACP-G010
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/release_rights.json, test/formal_assurance/test_facp_007_release_inventory.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/release_rights.json, test/formal_assurance/test_facp_007_release_inventory.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_007_release_inventory.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/release
- Parallel lane: facp-inventory-3
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: inspect exact Git DAGs, locks, manifests, receipts, licenses, and build metadata; write report/test
- Prohibited effects: fetch or update dependencies; sign or publish; infer legal clearance
- Conflict policy: Own only the release/rights inventory artifacts.
- Preconditions: Controller source binding is committed and clean.
- Evidence subset: mutable revisions, gitlink ancestry, campaign divergence, stale receipts, package/repository license conflicts, missing provenance, reproducibility inputs
- Acceptance: Every mutable/unknown/stale qualification input is identified with exact source and blocking predicate; historical receipts are separated from current-tree qualification.

## FACP-008 Build the unified claim inventory and seeded defect corpus

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: source-inventory
- Depends on: FACP-001, FACP-002, FACP-003, FACP-004, FACP-005, FACP-006, FACP-007
- Goal id: FACP-G010
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/baseline/claim_inventory.json, implementation_plan/formal_assurance_control_plane/baseline/defect_corpus.jsonl, implementation_plan/formal_assurance_control_plane/baseline/trusted_computing_base.json, test/formal_assurance/test_facp_008_baseline_fanin.py
- Predicted files: implementation_plan/formal_assurance_control_plane/baseline/claim_inventory.json, implementation_plan/formal_assurance_control_plane/baseline/defect_corpus.jsonl, implementation_plan/formal_assurance_control_plane/baseline/trusted_computing_base.json, test/formal_assurance/test_facp_008_baseline_fanin.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_008_baseline_fanin.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/inventory/fanin
- Parallel lane: facp-fanin
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: normalize admitted inventory records; write corpus/TCB/test
- Prohibited effects: omit conflicting evidence; classify discovery as proof; mutate inspected repositories
- Conflict policy: Sole fan-in for FACP-001 through FACP-007; source reports are immutable inputs.
- Preconditions: All seven inventory tasks are complete on the same source forest.
- Evidence subset: canonical claim vocabulary, exact source spans, defect families, expected counterexamples, compatible component map, formal-tool capabilities and absence
- Acceptance: Corpus contains all roadmap seeds with expected disposition and mutation oracle; TCB names versions/assumptions; every planned task traces to at least one inventory fact or normative requirement.

## FACP-009 Specify the multidimensional evidence product algebra

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-proof
- Depends on: FACP-008
- Goal id: FACP-G110
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/docs/spec/formal-claim-algebra-v1.md, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_spec.py
- Predicted files: Mcp-Plus-Plus/docs/spec/formal-claim-algebra-v1.md, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_spec.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_spec.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/spec
- Parallel lane: facp-fca-proof
- Resource class: cpu-small
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add normative spec and structural conformance test
- Prohibited effects: collapse dimensions into a total ladder; claim proof before Lean checking
- Conflict policy: Sole owner of the FCA normative prose and vocabulary.
- Preconditions: FACP-008 inventory and TCB are current.
- Evidence subset: origin, integrity, authority, policy, proof, freshness, effect, environment, review dimensions and closed outcomes
- Acceptance: Vocabulary is closed, bounded, nonoverlapping, explicitly distinguishes discovery/authenticity/truth/observation/live qualification, and maps every seeded legacy claim without unsafe promotion.

## FACP-010 Define promotion predicates and compatibility rules

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-proof
- Depends on: FACP-009
- Goal id: FACP-G110
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/schemas/assurance/v1/promotion-rules.json, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_promotion_rules.py
- Predicted files: Mcp-Plus-Plus/schemas/assurance/v1/promotion-rules.json, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_promotion_rules.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_promotion_rules.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/predicates
- Parallel lane: facp-fca-proof
- Resource class: cpu-small
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add machine-readable transition/promotion rules and tests
- Prohibited effects: label-only promotion; evidence fabrication; permissive unknown transition
- Conflict policy: Sole owner of the promotion-rules artifact.
- Preconditions: FCA vocabulary is stable.
- Evidence subset: production_supported, effect_successful, proof_reusable, receipt_authoritative, release_admissible, conservative legacy mappings
- Acceptance: Each predicate names necessary dimensions and evidence; non-implications such as digest-to-truth, payment-to-authority, hermetic-to-live, and fixture-to-observed are executable negative rules.

## FACP-011 Encode FCA definitions and transitions in Lean

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-proof
- Depends on: FACP-010
- Goal id: FACP-G110
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/formal/lean/FormalClaimAlgebra/Basic.lean, Mcp-Plus-Plus/formal/lean/lakefile.toml, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_lean_build.py
- Predicted files: Mcp-Plus-Plus/formal/lean/FormalClaimAlgebra/Basic.lean, Mcp-Plus-Plus/formal/lean/lakefile.toml, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_lean_build.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_lean_build.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/lean-basic
- Parallel lane: facp-fca-proof
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add hermetic Lean project and definitions using pinned installed toolchain
- Prohibited effects: network dependency resolution; admitted theorem; generated success receipt without compiler exit zero
- Conflict policy: Own only Basic.lean, lakefile, and the build test.
- Preconditions: Lean capability/version is recorded in the TCB; promotion rules are stable.
- Evidence subset: inductive dimensions, decidable equality, transition relation, predicate definitions, structural correspondence to JSON rules
- Acceptance: Lean builds offline; definitions are closed/decidable; a generated parity check proves names and transition cases match the normative rules.

## FACP-012 Prove the illegal-promotion theorem suite

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-proof
- Depends on: FACP-011
- Goal id: FACP-G110
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/formal/lean/FormalClaimAlgebra/Promotion.lean, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_theorems.py
- Predicted files: Mcp-Plus-Plus/formal/lean/FormalClaimAlgebra/Promotion.lean, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_theorems.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_theorems.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/lean-theorems
- Parallel lane: facp-fca-proof
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add theorem file and proof-checking test
- Prohibited effects: sorry/admit/axiom escape; theorem naming without checked proof
- Conflict policy: Own only Promotion.lean and its proof test.
- Preconditions: FACP-011 Lean definitions build.
- Evidence subset: fixture, simulation, declaration, unchecked hash, browser policy, expired/revoked delegation, stale receipt, unknown effect, payment/peer nonauthority
- Acceptance: Lean checks every forbidden-promotion theorem with no prohibited declarations; test parses compiler output and records exact Lean/toolchain/source identity.

## FACP-013 Implement the executable Rust FCA kernel

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-010, FACP-012
- Goal id: FACP-G120
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tests-rs/src/formal_claim_algebra.rs, Mcp-Plus-Plus/tests-rs/tests/formal_claim_algebra_test.rs
- Predicted files: Mcp-Plus-Plus/tests-rs/src/formal_claim_algebra.rs, Mcp-Plus-Plus/tests-rs/tests/formal_claim_algebra_test.rs
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_rust.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/rust
- Parallel lane: facp-fca-runtime
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add closed enums, validated constructors, predicates, and Rust tests
- Prohibited effects: public unchecked production-success constructor; silently default unknown enum; network dependencies
- Conflict policy: Sole owner of new Rust FCA module and test.
- Preconditions: Lean theorem and machine-readable rules agree.
- Evidence subset: constructor rejection, transition parity, exhaustive pattern matching, canonical serialization hooks
- Acceptance: Rust accepts/rejects every normative vector; illegal transitions cannot construct a success type through public APIs; cargo test is invoked by the Python hermetic wrapper.

## FACP-014 Adapt existing supervisor assurance records to FCA

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-001, FACP-013
- Goal id: FACP-G120
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/assurance/formal_claim_adapter.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_adapter.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/assurance/formal_claim_adapter.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_adapter.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_adapter.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/accelerate-adapter
- Parallel lane: facp-fca-adapter-1
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add compatibility adapter and tests; import existing proof/evidence contracts
- Prohibited effects: edit existing ladders in this task; broaden legacy evidence; claim deprecation complete
- Conflict policy: Own only the new adapter/test; shared exports are deferred to migration fan-in.
- Preconditions: Reusable-primitives inventory and Rust semantics are current.
- Evidence subset: AssuranceLevel, EvidenceTier, proof receipts/caches, execution permits, capability records, stale/unknown cases
- Acceptance: Every legacy record maps to an FCA envelope or typed incompatibility; absent dimensions remain unchecked/absent; reverse projection refuses information-losing promotion.

## FACP-015 Adapt Kit evidence and proof-role records to FCA

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-004, FACP-013
- Goal id: FACP-G120
- Owning repository: external/ipfs_kit
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance/formal_claim_adapter.py, external/ipfs_kit/tests/test_formal_claim_adapter.py
- Predicted files: external/ipfs_kit/ipfs_kit_py/assurance/formal_claim_adapter.py, external/ipfs_kit/tests/test_formal_claim_adapter.py
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_claim_adapter.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/kit-adapter
- Parallel lane: facp-fca-adapter-2
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add lossless adapter/test around current support and proof-seal records
- Prohibited effects: weaken current Kit invariants; promote configured/hermetic/candidate evidence
- Conflict policy: Own only the new assurance adapter and dedicated test.
- Preconditions: Kit inventory and Rust semantics are current.
- Evidence subset: hermetic/conditional/live, absent/configured/selectable, candidate/admitted/current, freshness, ambiguous recovery, CAS identity
- Acceptance: Round trip preserves every Kit distinction; unsupported or ambiguous records remain nonqualifying; adapter tests prove zero-qualified state remains valid.

## FACP-016 Define EvidenceEnvelope@1 and normative transition vectors

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-010, FACP-013
- Goal id: FACP-G120
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/schemas/assurance/v1/evidence-envelope.schema.json, Mcp-Plus-Plus/conformance/vectors/formal_claim_algebra.json, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_vectors_schema.py
- Predicted files: Mcp-Plus-Plus/schemas/assurance/v1/evidence-envelope.schema.json, Mcp-Plus-Plus/conformance/vectors/formal_claim_algebra.json, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_vectors_schema.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_vectors_schema.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/vectors
- Parallel lane: facp-fca-runtime
- Resource class: cpu-small
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add strict schema, positive/negative/mutation vectors, and schema test
- Prohibited effects: unknown normative fields; duplicate keys; floats; unbounded strings; permissive default
- Conflict policy: Sole owner of EvidenceEnvelope schema and FCA vector file.
- Preconditions: Promotion rules and Rust public model are stable.
- Evidence subset: valid states, illegal promotions, malformed combinations, stale/revoked/unknown cases, mutation oracle
- Acceptance: Schema is closed and bounded; every theorem case has at least one negative vector; one-field mutations fail for the declared reason and stable error code.

## FACP-017 Generate the Python FCA binding and validator

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-013, FACP-016
- Goal id: FACP-G120
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tests-py/validators/formal_claim_algebra.py, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_python.py
- Predicted files: Mcp-Plus-Plus/tests-py/validators/formal_claim_algebra.py, Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_python.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_python.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/python
- Parallel lane: facp-fca-binding-1
- Resource class: cpu-small
- Implementation mode: generated-deterministic
- Provider authority: none
- Allowed effects: generate closed Python model/validator and tests from FCA source
- Prohibited effects: hand-maintained divergent enum; import-time installer/network; permissive extra fields
- Conflict policy: Own only Python FCA generated source and test.
- Preconditions: EvidenceEnvelope schema and vectors are stable.
- Evidence subset: strict parse/serialize, validated promotion, stable errors, compatibility construction
- Acceptance: Python passes all normative vectors, rejects unknown fields and illegal transitions, and cold imports without network/process/write effects.

## FACP-018 Generate the TypeScript FCA binding and validator

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims-runtime
- Depends on: FACP-013, FACP-016
- Goal id: FACP-G120
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tests-ts/src/formalClaimAlgebra.ts, Mcp-Plus-Plus/tests-ts/src/__tests__/formalClaimAlgebra.test.ts
- Predicted files: Mcp-Plus-Plus/tests-ts/src/formalClaimAlgebra.ts, Mcp-Plus-Plus/tests-ts/src/__tests__/formalClaimAlgebra.test.ts
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_typescript.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/typescript
- Parallel lane: facp-fca-binding-2
- Resource class: cpu-small
- Implementation mode: generated-deterministic
- Provider authority: none
- Allowed effects: generate closed TypeScript model/validator and tests from FCA source
- Prohibited effects: browser authority constructor; permissive extra fields; divergent enum
- Conflict policy: Own only TypeScript FCA generated source and test.
- Preconditions: EvidenceEnvelope schema and vectors are stable.
- Evidence subset: strict parse/serialize, validated promotion, stable errors, browser-safe projection
- Acceptance: TypeScript passes all normative vectors and cannot construct authority/observation dimensions from browser-supplied policy or consent fields.

## FACP-019 Add the repository-wide ambiguous-claim scanner

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: claim-scanner
- Depends on: FACP-008, FACP-010, FACP-016
- Goal id: FACP-G130
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_claim_scanner.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_scanner.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_claim_scanner.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_scanner.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_claim_scanner.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/scanner
- Parallel lane: facp-fca-scanner
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: extend existing AST/index interfaces; emit source-bound findings
- Prohibited effects: raw full-repository context dump; automatic source edit; classify naming alone as defect
- Conflict policy: Own new scanner/test only; consume existing repository indexes without editing them.
- Preconditions: Claim inventory and normative vocabulary are current.
- Evidence subset: success, available, supported, verified, proven, authorized, allowed, current, production, capability, mock, simulation, fallback, CID fields
- Acceptance: Scanner finds seeded source spans with abstract trace and repair family, distinguishes typed compatibility aliases, and has a low-noise allowlist that cannot suppress corpus defects.

## FACP-020 Seal formal-claim-algebra-v1 conformance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-claims
- Depends on: FACP-012, FACP-014, FACP-015, FACP-017, FACP-018, FACP-019
- Goal id: FACP-G100
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/gates/formal_claim_algebra_v1.json, test/formal_assurance/test_facp_020_fca_gate.py
- Predicted files: implementation_plan/formal_assurance_control_plane/gates/formal_claim_algebra_v1.json, test/formal_assurance/test_facp_020_fca_gate.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_020_fca_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/fca/gate
- Parallel lane: facp-fanin
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: execute hermetic Lean/Rust/Python/TypeScript/vector/scanner gates; write signed-content gate record
- Prohibited effects: mark migrated paths complete; accept stale or partial language results; provider-authored completion
- Conflict policy: Sole FCA fan-in; producer artifacts are immutable inputs.
- Preconditions: All FCA theorem, adapter, binding, and scanner tasks completed for the same source forest.
- Evidence subset: theorem/toolchain identities, vector digests, cross-language transition matrix, compatibility loss report, scanner corpus score
- Acceptance: All implementations agree; no forbidden promotion is constructible; no unqualified production claim is newly introduced; receipt binds exact source/dependencies and explicitly excludes the four-path migration until FACP-031.

## FACP-021 Characterize Datasets cold-import effects

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-migration
- Depends on: FACP-003, FACP-017, FACP-020
- Goal id: FACP-G210
- Owning repository: external/ipfs_datasets
- Outputs: external/ipfs_datasets/tests/unit/test_formal_assurance_import_purity.py, external/ipfs_datasets/docs/architecture/FORMAL_ASSURANCE_IMPORT_BASELINE.md
- Predicted files: external/ipfs_datasets/tests/unit/test_formal_assurance_import_purity.py, external/ipfs_datasets/docs/architecture/FORMAL_ASSURANCE_IMPORT_BASELINE.md
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/test_formal_assurance_import_purity.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/datasets-import
- Parallel lane: facp-migrate-datasets
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add sandboxed import tests and baseline documentation; deny network/process/write during probe
- Prohibited effects: change package import in this task; install dependencies; treat test observation as formal proof
- Conflict policy: Own only the import-purity test and baseline document.
- Preconditions: Datasets inventory and FCA Python binding are current.
- Evidence subset: top-level call graph, environment/PATH mutation, installer, network, subprocess, persistent write, time/memory bounds
- Acceptance: Test fails on every seeded import effect, runs from empty explicit state/home equivalents without network/process writes, and records exact observed legacy behavior without normalizing it as success.

## FACP-022 Move Datasets installation behind explicit initialization

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-migration
- Depends on: FACP-021
- Goal id: FACP-G210
- Owning repository: external/ipfs_datasets
- Outputs: external/ipfs_datasets/ipfs_datasets_py/assurance/initialization.py, external/ipfs_datasets/tests/unit/test_formal_assurance_explicit_initialization.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/assurance/initialization.py, external/ipfs_datasets/tests/unit/test_formal_assurance_explicit_initialization.py
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/test_formal_assurance_explicit_initialization.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/datasets-init
- Parallel lane: facp-migrate-datasets
- Resource class: cpu-medium
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: implement explicit initializer, explicit state root, lazy compatibility hook, and package-root fan-in
- Prohibited effects: initialize or install on import; network in tests; swallow initialization error; implicit home state
- Conflict policy: This task is the sole Datasets package-root fan-in; preserve unrelated exports.
- Preconditions: Import-purity baseline reliably detects legacy effects.
- Evidence subset: explicit call boundary, typed Unavailable/Failed, idempotent initialization, pure cold import, compatibility warning
- Acceptance: Core import passes the sandbox test; installation requires an explicit authorized call and state root; missing dependencies return typed non-success; legacy opt-in cannot silently default on.

## FACP-023 Replace Datasets false-success fallbacks

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-migration
- Depends on: FACP-017, FACP-020, FACP-022
- Goal id: FACP-G210
- Owning repository: external/ipfs_datasets
- Outputs: external/ipfs_datasets/ipfs_datasets_py/assurance/outcomes.py, external/ipfs_datasets/tests/unit/test_formal_assurance_dataset_outcomes.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/assurance/outcomes.py, external/ipfs_datasets/tests/unit/test_formal_assurance_dataset_outcomes.py
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/test_formal_assurance_dataset_outcomes.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/datasets-outcomes
- Parallel lane: facp-migrate-datasets
- Resource class: cpu-medium
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: add FCA outcome adapter and migrate bounded download/upload/semantic result call sites
- Prohibited effects: generic success fallback; simulated result in production; change unrelated semantic API
- Conflict policy: Own new outcome adapter/test and exact inventoried fallback sites only.
- Preconditions: Explicit initialization and FCA binding pass.
- Evidence subset: Unavailable, Attempted, Unknown, Observed, Verified, Failed; effect-observation binding; delegated receipt validation
- Acceptance: Missing backend/dependency returns Unavailable; attempted-but-unobserved is not success; Verified requires admitted verifier evidence; compatibility projection preserves non-success disposition.

## FACP-024 Add Accelerate mock-origin rejection tests

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accelerate-migration
- Depends on: FACP-002, FACP-014, FACP-020
- Goal id: FACP-G220
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/test/api/test_formal_assurance_mock_origin.py, external/ipfs_accelerate/test/fixtures/formal_assurance/mock_origin_cases.json
- Predicted files: external/ipfs_accelerate/test/api/test_formal_assurance_mock_origin.py, external/ipfs_accelerate/test/fixtures/formal_assurance/mock_origin_cases.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_formal_assurance_mock_origin.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/accelerate-mock
- Parallel lane: facp-migrate-accelerate
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add adversarial fixtures/tests around inventoried flows
- Prohibited effects: execute real provider; edit production behavior; treat fixture completion as live evidence
- Conflict policy: Own only mock-origin fixtures and tests.
- Preconditions: Accelerate inventory and FCA supervisor adapter pass.
- Evidence subset: mock worker, hardware, inference handler, fallback, dependency injection, compatibility namespace, production registry sinks
- Acceptance: Each seeded mock source reaches the expected legacy sink before repair and is classified simulated; same-name real/fixture decoys are distinguished by provenance rather than naming.

## FACP-025 Migrate Accelerate capability and inference outcomes

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accelerate-migration
- Depends on: FACP-024
- Goal id: FACP-G220
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/assurance/capability_outcomes.py, external/ipfs_accelerate/test/api/test_formal_assurance_capability_outcomes.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/assurance/capability_outcomes.py, external/ipfs_accelerate/test/api/test_formal_assurance_capability_outcomes.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_formal_assurance_capability_outcomes.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/accelerate-outcomes
- Parallel lane: facp-migrate-accelerate
- Resource class: cpu-large
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: add probe-backed capability/outcome adapter and isolate inventoried simulation call sites
- Prohibited effects: mock production registration; fallback success; live route to simulated provider; broad coordinator rewrite
- Conflict policy: Own new adapter/test and exact inventoried capability/inference integration seams.
- Preconditions: Mock-origin tests are red before and green after the migration.
- Evidence subset: probe identity/freshness, simulation namespace, observed/delegated result, explicit unknown outcome, compatibility refusal
- Acceptance: Non-CPU routing requires current capability evidence; simulation remains selectable only in explicit test mode; inference returns observed/delegated evidence, Unknown, Unavailable, or Failed, never invented success.

## FACP-026 Replace Accelerate pseudo-CID paths

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accelerate-migration
- Depends on: FACP-002, FACP-006, FACP-016, FACP-020
- Goal id: FACP-G220
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/assurance/content_identity.py, external/ipfs_accelerate/test/api/test_formal_assurance_content_identity.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/assurance/content_identity.py, external/ipfs_accelerate/test/api/test_formal_assurance_content_identity.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_formal_assurance_content_identity.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/accelerate-cid
- Parallel lane: facp-migrate-accelerate
- Resource class: cpu-medium
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: call existing canonical multiformats/CID code; recompute content identity; migrate inventoried pseudo-CID sites
- Prohibited effects: regex-only validation; raw hex or Qm-prefix fabrication; introduce another codec
- Conflict policy: Own new identity adapter/test and exact inventoried pseudo-CID sites.
- Preconditions: MCP++ identity inventory and EvidenceEnvelope vectors pass.
- Evidence subset: canonical bytes, fixed codec/multihash profile, decode/recompute, mutation rejection, stable errors
- Acceptance: Raw SHA-256 hex and truncated Qm-like values fail; canonical values decode and recompute against bytes; one-bit content or identifier mutation fails with the expected integrity state.

## FACP-027 Enforce Kit current live-backend qualification

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-migration
- Depends on: FACP-004, FACP-015, FACP-020
- Goal id: FACP-G230
- Owning repository: external/ipfs_kit
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance/live_backend_gate.py, external/ipfs_kit/tests/test_formal_assurance_live_backend_gate.py
- Predicted files: external/ipfs_kit/ipfs_kit_py/assurance/live_backend_gate.py, external/ipfs_kit/tests/test_formal_assurance_live_backend_gate.py
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_live_backend_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/kit-live
- Parallel lane: facp-migrate-kit
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add FCA selection gate and integrate exact backend selector seam
- Prohibited effects: run live backend; promote registration/configuration/hermetic evidence; change backend implementations
- Conflict policy: Own new gate/test and one reviewed selector integration seam.
- Preconditions: Kit adapter preserves the current support matrix.
- Evidence subset: backend/operation/environment identity, live observation, freshness/expiry, signature, source release, limitations
- Acceptance: Storage selection requires current live evidence; stale/degraded/revoked demote automatically; no qualified backend yields typed Unavailable without fallback success.

## FACP-028 Enforce Kit proof-role and freshness transitions

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-migration
- Depends on: FACP-004, FACP-015, FACP-020
- Goal id: FACP-G230
- Owning repository: external/ipfs_kit
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance/proof_role_gate.py, external/ipfs_kit/tests/test_formal_assurance_proof_role_gate.py
- Predicted files: external/ipfs_kit/ipfs_kit_py/assurance/proof_role_gate.py, external/ipfs_kit/tests/test_formal_assurance_proof_role_gate.py
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_proof_role_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/kit-proof
- Parallel lane: facp-migrate-kit
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add FCA proof-role gate and integrate exact admission/current-pointer seam
- Prohibited effects: decide logical validity in Kit; update current on unknown/ambiguous/stale; weaken CAS/WAL
- Conflict policy: Own new gate/test and one reviewed proof-store integration seam.
- Preconditions: Kit adapter and current proof-store tests pass.
- Evidence subset: candidate/admitted/current, verifier identity, proof key, source closure, freshness, CAS expected root, ambiguous recovery
- Acceptance: Candidate never implies admitted; admitted stale evidence cannot become current; unknown verifier outcome persists explicitly; concurrent pointer changes fail CAS and retain immutable history.

## FACP-029 Prove SwissKnife browser nonauthority

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: swissknife-migration
- Depends on: FACP-005, FACP-018, FACP-020
- Goal id: FACP-G240
- Owning repository: swissknife
- Outputs: swissknife/test/formal-assurance/browser-nonauthority.test.ts, swissknife/test/formal-assurance/browser-authority-vectors.json
- Predicted files: swissknife/test/formal-assurance/browser-nonauthority.test.ts, swissknife/test/formal-assurance/browser-authority-vectors.json
- Validation: python3 -m pytest test/formal_assurance/test_facp_029_swissknife_browser_vectors.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/swissknife-nonauthority
- Parallel lane: facp-migrate-swissknife
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add negative TypeScript vectors/tests and Python harness
- Prohibited effects: browser network/host effect; source repair in this task; treat UI confirmation as authority
- Conflict policy: Own only browser-nonauthority fixtures/tests.
- Preconditions: SwissKnife inventory and TypeScript FCA binding pass.
- Evidence subset: allow/deny, consent granted/absent, tenant/workspace, dry-run/live, changed arguments, replay, expiry
- Acceptance: Paired requests differing only in browser authority fields produce identical host authorization inputs/results; legacy default-granted behavior is a failing seed, not accepted evidence.

## FACP-030 Migrate SwissKnife to host-issued FCA outcomes

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: swissknife-migration
- Depends on: FACP-029
- Goal id: FACP-G240
- Owning repository: swissknife
- Outputs: swissknife/src/services/mcp/formalAssuranceGateway.ts, swissknife/test/formal-assurance/host-admission-projection.test.ts
- Predicted files: swissknife/src/services/mcp/formalAssuranceGateway.ts, swissknife/test/formal-assurance/host-admission-projection.test.ts
- Validation: python3 -m pytest test/formal_assurance/test_facp_030_swissknife_host_projection.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/swissknife-host
- Parallel lane: facp-migrate-swissknife
- Resource class: cpu-medium
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: add browser request/host decision projection and migrate exact inventoried gateway path
- Prohibited effects: construct allow/policy/authority in browser; transmit raw credential/host path; silently grant consent
- Conflict policy: Own new gateway/test and exact inventoried live gateway seam.
- Preconditions: Browser-nonauthority negative suite is stable.
- Evidence subset: canonical request, actor/session opaque refs, method/resource/argument CID, host decision, confirmation request, evidence classification
- Acceptance: Browser sends no authority decision; default consent is absent; UI displays exact method/resource/argument digest and consumes host-provided typed outcome without upgrading evidence.

## FACP-031 Seal the four-path FCA day-90 gate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: fca-migration
- Depends on: FACP-022, FACP-023, FACP-025, FACP-026, FACP-027, FACP-028, FACP-030
- Goal id: FACP-G200
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/gates/day90_four_path.json, test/formal_assurance/test_facp_031_four_path_gate.py
- Predicted files: implementation_plan/formal_assurance_control_plane/gates/day90_four_path.json, test/formal_assurance/test_facp_031_four_path_gate.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_031_four_path_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/migration/gate
- Parallel lane: facp-fanin
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: execute hermetic cross-repository regression/mutation gate; write exact-tree receipt
- Prohibited effects: live external effect; release claim; waive a missing migration; infer rights
- Conflict policy: Sole four-path fan-in; migrated repository commits are immutable inputs.
- Preconditions: All four migration lanes complete against the same source forest.
- Evidence subset: import purity, typed outcomes, mock provenance, canonical CID, live qualification, proof roles, browser nonauthority, ambiguous-claim scan
- Acceptance: No migrated path exhibits import mutation, false success, mock-to-live, pseudo-CID, hermetic-to-live, candidate-to-current, or browser-to-authority promotion; gate binds all exact commits and limitations.

## FACP-032 Extend MCP++ IDL with OperationSpec@1

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-006, FACP-020, FACP-031
- Goal id: FACP-G310
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/docs/spec/assurance-idl.md, Mcp-Plus-Plus/schemas/assurance/v1/operation-spec.schema.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_spec.py
- Predicted files: Mcp-Plus-Plus/docs/spec/assurance-idl.md, Mcp-Plus-Plus/schemas/assurance/v1/operation-spec.schema.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_spec.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_spec.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/idl
- Parallel lane: facp-contracts
- Resource class: cpu-medium
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: extend existing MCP IDL with closed assurance fields and strict schema
- Prohibited effects: add a new MCP++ profile; duplicate existing operation identity; unknown normative fields
- Conflict policy: Sole owner of Assurance IDL spec and OperationSpec schema.
- Preconditions: FCA and four-path gate establish stable semantics.
- Evidence subset: input/output/error, effect/resource/idempotency/reversibility, authority/policy/confirmation/lease/observation/evidence, size/time bounds
- Acceptance: OperationSpec is versioned, closed, bounded, no critical floats, and can describe all migrated operations without free-form authority or outcome fields.

## FACP-033 Fix the normative DAG-CBOR and CID profile

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-026, FACP-032
- Goal id: FACP-G310
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/docs/spec/assurance-canonical-encoding.md, Mcp-Plus-Plus/conformance/vectors/assurance-canonical-encoding.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_canonical_encoding_spec.py
- Predicted files: Mcp-Plus-Plus/docs/spec/assurance-canonical-encoding.md, Mcp-Plus-Plus/conformance/vectors/assurance-canonical-encoding.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_canonical_encoding_spec.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_canonical_encoding_spec.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/encoding
- Parallel lane: facp-contracts
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add normative encoding/CID profile, positive/negative/mutation vectors, and test
- Prohibited effects: multiple security-critical canonical forms; indefinite lengths; duplicate keys; floats; regex-only CID
- Conflict policy: Sole owner of canonical-encoding spec/vector.
- Preconditions: OperationSpec and canonical identity migration are current.
- Evidence subset: definite lengths, sorted maps, link encoding, decimal rules, unknown fields, fixed CID version/codec/multihash per family
- Acceptance: Every security-critical artifact has one deterministic byte representation; exact CID derivation is specified; duplicate/unknown/malleable encodings are negative vectors.

## FACP-034 Implement the Assurance IDL compiler core

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-032, FACP-033
- Goal id: FACP-G310
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tools/assurance_idl/compiler.py, Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_compiler.py
- Predicted files: Mcp-Plus-Plus/tools/assurance_idl/compiler.py, Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_compiler.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_idl_compiler.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/compiler
- Parallel lane: facp-contracts
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add provider-free parser/semantic checker/generator core and hermetic tests
- Prohibited effects: execute generated code; network; accept unknown constructs; non-deterministic output
- Conflict policy: Sole compiler-core owner; generated targets are separate later tasks.
- Preconditions: IDL and canonical encoding specs are stable.
- Evidence subset: schema/code/vector/error/docs/formal-skeleton generation inputs, stable ordering, bounded text/collections, exact diagnostics
- Acceptance: Same source produces byte-identical outputs across repeated clean runs; invalid contracts fail before generation with stable errors; compiler reads no credentials/network.

## FACP-035 Add Rust codec and independent translation validation

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-012, FACP-013, FACP-034
- Goal id: FACP-G310
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tests-rs/src/assurance_codec.rs, Mcp-Plus-Plus/tests-rs/tests/assurance_translation_validation_test.rs
- Predicted files: Mcp-Plus-Plus/tests-rs/src/assurance_codec.rs, Mcp-Plus-Plus/tests-rs/tests/assurance_translation_validation_test.rs
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_rust_translation_validation.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/rust-codec
- Parallel lane: facp-contracts-rust
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add strict Rust codec and independent vector validator
- Prohibited effects: trust generator output without validation; permissive decode; unchecked CID
- Conflict policy: Own only new Rust codec/validation files.
- Preconditions: Compiler core and FCA theorem/kernel are current.
- Evidence subset: parse-serialize inverse, serialize-parse canonicality, non-malleability, exact valid domain, normative CID
- Acceptance: Validator independently rejects all negative/mutation vectors and confirms canonical round trips/CIDs; result binds compiler and validator identities separately.

## FACP-036 Generate Python, TypeScript, Rust, and Go operation bindings

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-017, FACP-018, FACP-034
- Goal id: FACP-G310
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/tools/assurance_idl/generated_manifest.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_generated_bindings.py
- Predicted files: Mcp-Plus-Plus/tools/assurance_idl/generated_manifest.json, Mcp-Plus-Plus/tests-py/integration/test_assurance_generated_bindings.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assurance_generated_bindings.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/bindings
- Parallel lane: facp-contracts-bindings
- Resource class: cpu-large
- Implementation mode: generated-deterministic
- Provider authority: none
- Allowed effects: generate versioned language packages, schemas, errors, docs, vectors, fuzz dictionaries, and manifest
- Prohibited effects: hand edit generated targets; omit negative fixtures; language-specific semantic extension
- Conflict policy: Generator is the sole owner of all paths listed by generated_manifest; task output ownership is the manifest and its test.
- Preconditions: Compiler core and language FCA adapters pass.
- Evidence subset: EvidenceEnvelope, OperationSpec, AdmissionToken, EffectReceipt; Python/TS/Rust/Go parity; generated-file digests
- Acceptance: Clean generation is deterministic and complete; manifest maps every source contract to every projection; no duplicate hand-authored normative model remains on migrated paths.

## FACP-037 Seal cross-language canonical contract conformance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: canonical-contracts
- Depends on: FACP-035, FACP-036
- Goal id: FACP-G310
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/gates/canonical_contracts_v1.json, test/formal_assurance/test_facp_037_contract_conformance.py
- Predicted files: implementation_plan/formal_assurance_control_plane/gates/canonical_contracts_v1.json, test/formal_assurance/test_facp_037_contract_conformance.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_037_contract_conformance.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/contracts/gate
- Parallel lane: facp-fanin
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: execute clean cross-language conformance/mutation/fuzz subset; write exact-tree receipt
- Prohibited effects: accept missing language; network; trust compiler self-report as sole evidence
- Conflict policy: Sole contract fan-in; compiler and independent validator outputs are immutable inputs.
- Preconditions: Rust validator and all generated projections complete.
- Evidence subset: byte/CID parity, unknown/duplicate/mutation rejection, stable errors, generator determinism, independent validator
- Acceptance: Same semantic value produces byte-identical canonical bytes and CID in four languages; one-bit and unknown-field mutations fail; gate binds exact source/toolchains.

## FACP-038 Define effect classes and admission typestate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: effect-admission
- Depends on: FACP-031, FACP-032, FACP-037
- Goal id: FACP-G320
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/docs/spec/effect-admission-kernel.md, Mcp-Plus-Plus/schemas/assurance/v1/effect-admission.schema.json, Mcp-Plus-Plus/tests-py/integration/test_effect_admission_spec.py
- Predicted files: Mcp-Plus-Plus/docs/spec/effect-admission-kernel.md, Mcp-Plus-Plus/schemas/assurance/v1/effect-admission.schema.json, Mcp-Plus-Plus/tests-py/integration/test_effect_admission_spec.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_effect_admission_spec.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/admission/spec
- Parallel lane: facp-admission
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add normative effect/outcome/typestate/obligation contract and tests
- Prohibited effects: open effect vocabulary; payment/peer/browser authority; policy unknown-to-allow
- Conflict policy: Sole owner of admission normative spec/schema.
- Preconditions: Four-path and canonical-contract gates pass.
- Evidence subset: Pure/read/write/process/credential/install/repository/publish/payment/private/legal/irreversible effects; Proposed-to-ReceiptSealed and terminal states
- Acceptance: Every migrated operation is classified; token obligations are mechanically derived; Unknown and CompensationRequired are explicit; only kernel-issued token unlocks a handler.

## FACP-039 Implement the restricted Effect Admission Kernel

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: effect-admission
- Depends on: FACP-014, FACP-037, FACP-038
- Goal id: FACP-G320
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission/formal_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_admission_kernel.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission/formal_kernel.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_admission_kernel.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_admission_kernel.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/admission/kernel
- Parallel lane: facp-admission
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add provider-free kernel around existing authorization/UCAN/policy/permit primitives and tests
- Prohibited effects: invoke effect handler; model/prompt/browser token construction; permissive policy translation; import network client
- Conflict policy: Own new admission module/test; adapt existing authority primitives without rewriting them.
- Preconditions: Effect typestate and canonical token codec are stable.
- Evidence subset: actor/device/tenant/resource/operation/argument/contract/delegation/policy/confirmation/lease/expiry/nonce/signature/revocation
- Acceptance: Valid token requires all declared obligations and exact argument CID; expired/revoked/replayed/changed arguments fail; unknown source policy compiles only to denial/obligation or typed indeterminate.

## FACP-040 Route migrated Accelerate transports through admission

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: effect-admission
- Depends on: FACP-025, FACP-039
- Goal id: FACP-G320
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission/transport_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transport_gate.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/admission/transport_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transport_gate.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transport_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/admission/transports
- Parallel lane: facp-admission
- Resource class: cpu-large
- Implementation mode: bounded-repair
- Provider authority: proposal-only
- Allowed effects: add common host gate and integrate migrated CLI/MCP/MCP++ handler seams
- Prohibited effects: bypass per transport; execute provider in tests; trust caller-selected tenant/policy/endpoint/path
- Conflict policy: Own new gate/test and exact inventoried migrated transport seams.
- Preconditions: Admission kernel and migrated capability outcomes pass.
- Evidence subset: same token/decision across transports, effect-class match, exact args, revocation, denial, typed observation outcome
- Acceptance: Direct handler call without token fails; all migrated transports make the same kernel call; browser/model/peer inputs cannot select authority; denied admission has zero handler invocations.

## FACP-041 Connect SwissKnife and seal the EAK negative gate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: effect-admission
- Depends on: FACP-030, FACP-040
- Goal id: FACP-G320
- Owning repository: root with SwissKnife and Accelerate adapters
- Outputs: swissknife/src/services/mcp/admissionTokenClient.ts, test/formal_assurance/test_facp_041_effect_admission_gate.py
- Predicted files: swissknife/src/services/mcp/admissionTokenClient.ts, test/formal_assurance/test_facp_041_effect_admission_gate.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_041_effect_admission_gate.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/admission/gate
- Parallel lane: facp-fanin
- Resource class: cpu-large
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add host-token client projection and execute hermetic cross-boundary negative tests
- Prohibited effects: live host effect; expose token secret/private context; browser token construction; weaken kernel policy
- Conflict policy: Sole EAK fan-in; owns new SwissKnife client and root gate test only.
- Preconditions: SwissKnife host projection and common transport gate pass.
- Evidence subset: browser allow/consent/dry-run nonauthority, one-use confirmation, argument binding, replay/expiry/revocation, all-transport kernel identity
- Acceptance: Changing browser authority fields never changes host authorization; changed arguments/actor/resource/policy/expiry/nonce fail; no migrated effect occurs before valid admission; receipt records exact observation or non-success.

## FACP-042 Extend static analysis with IPA product domains

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: abstract-interpretation
- Depends on: FACP-008, FACP-019, FACP-020
- Goal id: FACP-G410
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipa_formal_assurance.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipa_formal_assurance.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipa_formal_assurance.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/static/ipa
- Parallel lane: facp-static
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: extend existing Python/TypeScript AST, call graph, provenance, and Datalog adapters with bounded product domains
- Prohibited effects: import analyzed packages; auto-install Souffle; trust naming alone; emit full source bodies
- Conflict policy: Own new IPA module/test; consume existing indexes through public interfaces without editing them.
- Preconditions: Seed corpus, FCA scanner, and claim semantics are stable.
- Evidence subset: effect/trust/result/identity domains, import purity, mock flow, success without observation, exception swallowing, raw/pseudo-CID, CEGAR trace
- Acceptance: Analyzer finds every seeded defect with source-to-sink trace and stable rule ID; unavailable Souffle yields a typed capability record with a hermetic reference evaluator, not skipped analysis; spurious paths can refine without suppressing seeds.

## FACP-043 Add bounded IPA repair transforms and mutation gate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: abstract-interpretation
- Depends on: FACP-022, FACP-023, FACP-025, FACP-026, FACP-042
- Goal id: FACP-G410
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_transforms.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_transforms.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_transforms.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_transforms.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_transforms.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/static/repairs
- Parallel lane: facp-static
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add fixed AST/config transforms for explicit init, typed unavailable, simulation evidence, canonical CID, and critical error propagation
- Prohibited effects: general LLM edit; grammar expansion; transform outside admitted path; completion without byte mutation and reanalysis
- Conflict policy: Own new transform module/test; production application remains gated by FACP-051.
- Preconditions: Real pilots establish accepted target shapes and IPA reliably detects seeds.
- Evidence subset: before/after AST, preserved public compatibility, eliminated counterexample, no new abstract finding, exact write paths
- Acceptance: Each transform is deterministic/idempotent, rejects ambiguous targets, removes its seeded finding, preserves unrelated bytes, and returns a typed abstention when preconditions do not match.

## FACP-044 Add information-flow and noninterference assurance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: information-flow
- Depends on: FACP-041, FACP-042
- Goal id: FACP-G420
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/information_flow_assurance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_information_flow_assurance.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/information_flow_assurance.py, external/ipfs_accelerate/test/api/test_agent_supervisor_information_flow_assurance.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_information_flow_assurance.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/static/information-flow
- Parallel lane: facp-information-flow
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add security lattice, taint/declassification contracts, two-run symbolic tests, canaries, and redaction validation
- Prohibited effects: read real credentials/private matters; log secret values; browser authority declassification; claim general noninterference beyond checked kernel/bounds
- Conflict policy: Own new proof module/test; repository-specific labels arrive through adapters.
- Preconditions: EAK boundary and IPA facts are stable.
- Evidence subset: Public/Internal/RepositoryPrivate/TenantPrivate/MatterConfidential/Credential/CryptographicSecret/WitnessSecret; browser-host, tenant, prompt-authority, credential, witness properties
- Acceptance: Critical two-run suites pass; public logs/receipts/browser/prompts contain no protected raw value or host path; every allowed declassification binds policy, actor, destination, exact source, and purpose.

## FACP-045 Model transactional effect protocols

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: transactional-protocols
- Depends on: FACP-038, FACP-041
- Goal id: FACP-G510
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/formal/protocols/transactional_effects/TransactionalEffects.tla, Mcp-Plus-Plus/formal/protocols/transactional_effects/relational_invariants.als, Mcp-Plus-Plus/tests-py/integration/test_transactional_effect_models.py
- Predicted files: Mcp-Plus-Plus/formal/protocols/transactional_effects/TransactionalEffects.tla, Mcp-Plus-Plus/formal/protocols/transactional_effects/relational_invariants.als, Mcp-Plus-Plus/tests-py/integration/test_transactional_effect_models.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_transactional_effect_models.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/protocols/models
- Parallel lane: facp-protocols
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add bounded TLA+/Alloy models, capability probe, checked transition vectors, and syntax/reference tests
- Prohibited effects: auto-install formal tools; report model proof when unavailable; unbounded state exploration
- Conflict policy: Sole owner of transactional model directory and model test.
- Preconditions: Effect typestate and EAK negative gate pass.
- Evidence subset: admission, reservation, started/unknown/observed/receipt/current, lease/fence, retry/idempotency, crash, settlement, compensation, proof promotion
- Acceptance: Models encode all required invariants and crash boundaries; installed admitted tools produce checked traces, while missing tools produce explicit nonqualified capability evidence and leave live model-check gate unsatisfied.

## FACP-046 Enforce protocol/runtime trace conformance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: transactional-protocols
- Depends on: FACP-040, FACP-045
- Goal id: FACP-G510
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_transition_monitor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transition_monitor.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_transition_monitor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transition_monitor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_transition_monitor.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/protocols/runtime
- Parallel lane: facp-protocols
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add runtime event monitor, vector adapter, and crash/retry/fence tests
- Prohibited effects: execute irreversible external action; accept unknown transition; rewrite existing lease/WAL implementations
- Conflict policy: Own new monitor/test; consume existing runtime events through adapters.
- Preconditions: Transaction model transition table is stable.
- Evidence subset: prior/next state, protocol/instance/operation/actor, fence, idempotency, observation, time; NoDoubleEffect/NoStaleFence/NoSuccessWithoutObservation/NoConfirmationReuse/NoBlindUnknownRetry
- Acceptance: Monitor accepts exactly normative vectors, rejects stale fences/replay/incompatible idempotency/receipt arguments, and crash injection covers every persistent transition boundary in the harness.

## FACP-047 Extend semantic graphs into content-addressed capsules

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: semantic-invalidation
- Depends on: FACP-008, FACP-020, FACP-037, FACP-042
- Goal id: FACP-G610
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_capsule.py, external/ipfs_accelerate/test/api/test_agent_supervisor_semantic_capsule.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_capsule.py, external/ipfs_accelerate/test/api/test_agent_supervisor_semantic_capsule.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_semantic_capsule.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/incremental/capsules
- Parallel lane: facp-incremental
- Resource class: cpu-large
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: extend existing semantic dependency/provenance graphs with capsule schema, Datalog derivations, incremental update, and mutation tests
- Prohibited effects: raw repository dump as capsule; reuse on unknown dependency; rebuild parallel graph authority
- Conflict policy: Own new capsule module/test and adapt existing graph APIs without editing their semantics.
- Preconditions: Canonical contracts and IPA facts are stable.
- Evidence subset: exports/requires/effects/authority/abstract state/assumptions/guarantees/proofs/tests/public data/environment/source CIDs; invalidation/reuse path
- Acceptance: Clean rebuild equals incremental update; seeded semantic changes invalidate every required proof/test/release and no unrelated capsule; every reuse/invalidation has a minimal path explanation; stale historical receipts demote.

## FACP-048 Publish and compose repository assume-guarantee contracts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: assume-guarantee
- Depends on: FACP-028, FACP-031, FACP-041, FACP-046, FACP-047
- Goal id: FACP-G620
- Owning repository: Mcp-Plus-Plus
- Outputs: Mcp-Plus-Plus/schemas/assurance/v1/repository-contracts.json, Mcp-Plus-Plus/tests-py/integration/test_assume_guarantee_contracts.py
- Predicted files: Mcp-Plus-Plus/schemas/assurance/v1/repository-contracts.json, Mcp-Plus-Plus/tests-py/integration/test_assume_guarantee_contracts.py
- Validation: python3 -m pytest Mcp-Plus-Plus/tests-py/integration/test_assume_guarantee_contracts.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/composition/contracts
- Parallel lane: facp-composition
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add versioned contracts, environment discharge rules, counterexample fixtures, and composition tests
- Prohibited effects: assume away component defect; undisclosed environmental premise; repository import for contract discovery
- Conflict policy: Sole owner of normative repository-contract registry and test.
- Preconditions: Four migrations, EAK, TEP monitor, and semantic capsules pass.
- Evidence subset: Datasets pure semantics, Kit integrity/CAS/role separation, Accelerate admission/execution/observation, SwissKnife nonauthority/presentation
- Acceptance: Each assumption is supplied by a qualified guarantee or explicitly unresolved; seeded integration failures name the exact violated boundary; contract changes invalidate downstream capsules.

## FACP-049 Add translation receipts and deontic safety refinement

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: translation-validation
- Depends on: FACP-023, FACP-037, FACP-047, FACP-048
- Goal id: FACP-G630
- Owning repository: external/ipfs_datasets
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/translation_validation/formal_assurance.py, external/ipfs_datasets/tests/unit/logic/test_formal_assurance_translation_validation.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/translation_validation/formal_assurance.py, external/ipfs_datasets/tests/unit/logic/test_formal_assurance_translation_validation.py
- Validation: python3 -m pytest external/ipfs_datasets/tests/unit/logic/test_formal_assurance_translation_validation.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/translation/validation
- Parallel lane: facp-translation
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: extend canonical semantic API with TranslationReceipt, safety refinement, trusted rewrite registry, and adversarial tests
- Prohibited effects: claim equivalence without criteria; admit heuristic rewrite into proof extraction; silently drop modality/predicate/exception/time condition
- Conflict policy: Own new translation-validation module/test; use existing compiler/decompiler/e-graph interfaces.
- Preconditions: Datasets outcomes, canonical contracts, capsules, and repository contracts pass.
- Evidence subset: source/target/compiler CIDs, schemas, preservation class, equality criteria, loss, assumptions, obligations, recompilation/comparison, negation/exception/time/conflict/jurisdiction
- Acceptance: Unsupported/lossy constructs name exact loss; target never broadens source permission or removes prohibitions/obligations; proved or solver-validated rewrites are distinguished from heuristics; adversarial round trips have explicit dispositions.

## FACP-050 Extend proof cache and solver orchestration

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: proof-orchestration
- Depends on: FACP-012, FACP-047, FACP-049
- Goal id: FACP-G640
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/formal_assurance_orchestrator.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_orchestrator.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/formal_assurance_orchestrator.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_orchestrator.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_orchestrator.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/proof/orchestration
- Parallel lane: facp-proof
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: compose existing proof cache/router with capsule keys, incremental solver scopes, escalation ladder, conflict/explanation receipts
- Prohibited effects: unknown-to-verified; solver candidate as authority; cache reuse with changed closure; invoke LLM as assurance stage
- Conflict policy: Own new orchestrator/test; do not fork existing proof store or solver adapters.
- Preconditions: Lean theorem, semantic capsules, and translation receipts pass.
- Evidence subset: claim/spec/code/assumptions/environment/solver/revision/tactic key; schema/AI/Datalog/egraph/SMT/Alloy/TLA/specialized/Lean/human ladder
- Acceptance: Every result names assumptions/verifier/toolchain; cache reuse has formal unchanged/equivalent derivation; disagreement creates conflict; stronger escalation has reason/cost; unknown and unavailable remain nonverified.

## FACP-051 Add bounded counterexample-guided repair

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: cegis-repair
- Depends on: FACP-043, FACP-046, FACP-047, FACP-050
- Goal id: FACP-G710
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_cegis.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_cegis.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_cegis.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/synthesis/repair
- Parallel lane: facp-synthesis-repair
- Resource class: cpu-large
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add fixed repair grammars, candidate loop, isolated transaction, proof/test gate, PatchCertificate, and mutation benchmark
- Prohibited effects: unrestricted synthesis; grammar expansion by model; obligation waiver; source edit outside admitted paths; patch self-promotion
- Conflict policy: Own new CEGIS module/test; consume existing deterministic transforms and repair control plane.
- Preconditions: IPA transforms, TEP monitor, capsules, and proof orchestrator pass.
- Evidence subset: false success, mock capability, pseudo-CID, import effect, browser authority, mutable dependency, stale proof, missing lease/recovery, license conflict; parent/patch/affected capsules/obligations/results/residual risks
- Acceptance: Seeded corpus repairs either produce a minimal independently admitted PatchCertificate or typed abstention; original counterexample disappears, no new abstract/model/test counterexample appears, and scope/authority attacks fail.

## FACP-052 Synthesize or validate the bounded supervisor controller

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: reactive-control
- Depends on: FACP-041, FACP-045, FACP-048, FACP-050
- Goal id: FACP-G720
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_assurance_controller.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_controller.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/formal_assurance_controller.py, external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_controller.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_formal_assurance_controller.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/synthesis/controller
- Parallel lane: facp-synthesis-controller
- Resource class: cpu-proof-solver
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: synthesize or mechanically validate bounded controller/monitor for routing, retry, lease, human gate, proof escalation, compensation, shutdown
- Prohibited effects: arbitrary code synthesis; weaken hard property; unbounded retry; provider fallback changes authority/evidence; silent unrealizable specification
- Conflict policy: Own new controller/test; integrate through existing runtime policy seam only after validation.
- Preconditions: EAK, TEP models, repository contracts, and proof orchestrator pass.
- Evidence subset: hard safety, liveness under healthy assumptions, soft cost objectives, state machine, guards, runtime monitor, unrealizable core
- Acceptance: Hard properties hold in checked bounds; retries/parallelism are bounded; fallback preserves authority/evidence; unknown irreversible outcomes are not retried; unrealizable requirements return an explanatory core.

## FACP-053 Generate backend certification suites

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: backend-certification
- Depends on: FACP-027, FACP-028, FACP-037, FACP-046
- Goal id: FACP-G520
- Owning repository: external/ipfs_kit
- Outputs: external/ipfs_kit/ipfs_kit_py/assurance/backend_certification.py, external/ipfs_kit/tests/test_formal_assurance_backend_certification.py
- Predicted files: external/ipfs_kit/ipfs_kit_py/assurance/backend_certification.py, external/ipfs_kit/tests/test_formal_assurance_backend_certification.py
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_backend_certification.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/backend/generator
- Parallel lane: facp-backend
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add BackendContract-driven test/model/fault/receipt generator and hermetic self-tests
- Prohibited effects: live backend call in unit test; configuration-to-live promotion; certify unlisted backend; store credential
- Conflict policy: Own new generator/test; do not edit backend implementations.
- Preconditions: Kit gates, canonical contracts, and runtime monitor pass.
- Evidence subset: write/read-back/digest/delete/replay/timeout/concurrency/restart/corruption/large-object/credential/interface parity; environment/source/signature/freshness
- Acceptance: Generator deterministically produces required suites/receipt schema/support row; absent live runner yields Conditional/Unavailable evidence; no result can set LiveQualified without complete observed suite.

## FACP-054 Execute the local filesystem, pinned IPFS, and Iroh cohort

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: backend-certification
- Depends on: FACP-053
- Goal id: FACP-G520
- Owning repository: external/ipfs_kit
- Outputs: external/ipfs_kit/data/formal_assurance/backend_receipts/cohort.json, external/ipfs_kit/tests/test_formal_assurance_backend_cohort.py
- Predicted files: external/ipfs_kit/data/formal_assurance/backend_receipts/cohort.json, external/ipfs_kit/tests/test_formal_assurance_backend_cohort.py
- Validation: python3 -m pytest external/ipfs_kit/tests/test_formal_assurance_backend_cohort.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/backend/cohort
- Parallel lane: facp-backend
- Resource class: live-backend-bounded
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: run local durable filesystem suite; run IPFS/Iroh only when exact reviewed local capability/config/credentials permit; persist sanitized signed receipts
- Prohibited effects: install/start unknown daemon; remote destructive operation; fabricate missing live evidence; certify more than three targets
- Conflict policy: Sole owner of cohort receipt/test; live environment is lease-bound and nonparallel per backend.
- Preconditions: Generated suite passes hermetic self-test; live effects are separately authorized and bounded.
- Evidence subset: exact backend/runtime/config/source/environment, all required operations, observation digests, failure/limitation, time/expiry, signature
- Acceptance: Local filesystem has a current receipt if all observed operations pass; pinned IPFS and Iroh are LiveQualified only on complete current live evidence, otherwise explicitly Conditional/Unavailable with reasons; support matrix matches receipts.

## FACP-055 Implement release qualification and RightsIR

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: release-qualification
- Depends on: FACP-007, FACP-031, FACP-037, FACP-044, FACP-047, FACP-048, FACP-049, FACP-050, FACP-054
- Goal id: FACP-G810
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/release/qualification/release_predicate.json, implementation_plan/formal_assurance_control_plane/release/qualification/rights_ir.json, test/formal_assurance/test_facp_055_release_rights.py
- Predicted files: implementation_plan/formal_assurance_control_plane/release/qualification/release_predicate.json, implementation_plan/formal_assurance_control_plane/release/qualification/rights_ir.json, test/formal_assurance/test_facp_055_release_rights.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_055_release_rights.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/rights
- Parallel lane: facp-release-1
- Resource class: cpu-large
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: add machine-readable ReleaseAdmissible predicate, SPDX/rights graph, policy tests, and explicit human-review states
- Prohibited effects: definitive legal advice; unknown/conflict-to-compatible; release/sign/publish; mutable dependency acceptance
- Conflict policy: Own release predicate, RightsIR, and dedicated test only.
- Preconditions: Current qualification evidence, repository contracts, and proof orchestrator pass.
- Evidence subset: source/lock/build environment/tests/proofs/contracts/live capabilities/licenses/data/model rights/attribution/share-alike/commercial/redistribution/unknown custom
- Acceptance: Datasets license conflict and SwissKnife missing license/provenance block automatically; unknown rights remain human review; release predicate rejects stale proof, simulation-as-live, mutable ref, missing capability, incompatible contract, or unresolved mandatory rights.

## FACP-056 Add immutable lock, reproducible build, and signed provenance

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: release-qualification
- Depends on: FACP-055
- Goal id: FACP-G810
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/release/qualification/portfolio.lock.json, implementation_plan/formal_assurance_control_plane/release/qualification/provenance_policy.json, test/formal_assurance/test_facp_056_reproducible_supply_chain.py
- Predicted files: implementation_plan/formal_assurance_control_plane/release/qualification/portfolio.lock.json, implementation_plan/formal_assurance_control_plane/release/qualification/provenance_policy.json, test/formal_assurance/test_facp_056_reproducible_supply_chain.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_056_reproducible_supply_chain.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/supply-chain
- Parallel lane: facp-release-2
- Resource class: reproducible-build
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: create immutable portfolio lock/provenance policy; run two isolated builds within declared bounds; compare artifacts; generate unsigned test provenance
- Prohibited effects: publish/sign production release; resolve mutable branch during build; include credential; claim reproducibility from one build
- Conflict policy: Own lock/policy/test; build outputs are disposable and content-identified.
- Preconditions: Release/rights predicate stable and mandatory rights either resolved or explicitly human-blocked for nonrelease test.
- Evidence subset: commits/gitlinks/package locks/content hashes/toolchains/environment/instructions/SBOM/in-toto-style steps/SLSA-style provenance/bit identity
- Acceptance: All source dependencies are immutable and digest-bound; two clean environments produce bit-identical declared artifacts or a typed nonreproducible blocker; provenance verifies step materials/products and exact builder identity.

## FACP-057 Add evidence-checked documentation claims

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: release-qualification
- Depends on: FACP-019, FACP-055
- Goal id: FACP-G810
- Owning repository: external/ipfs_accelerate
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/evidence_checked_documentation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_evidence_checked_documentation.py
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/evidence_checked_documentation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_evidence_checked_documentation.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_evidence_checked_documentation.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/documentation
- Parallel lane: facp-release-3
- Resource class: cpu-medium
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: add controlled claim parser, ClaimIR requirement mapping, narrowing renderer, and fixtures
- Prohibited effects: auto-upgrade prose; treat Markdown/history as evidence; rewrite subjective human conclusions as proof
- Conflict policy: Own new documentation validator/test; documentation rewrites remain later reviewed effects.
- Preconditions: Ambiguous-claim scanner and release predicate stable.
- Evidence subset: supports, production-ready, formally verified, live, current, complete, authenticated, content-addressed, filing-ready, zero-knowledge, cryptographically proven
- Acceptance: Unsupported strong claims fail or render a narrower evidence-qualified statement; each claim links current exact evidence and freshness; human/heuristic conclusions remain labeled.

## FACP-058 Validate an independent cross-language conformance implementation

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: release-qualification
- Depends on: FACP-037, FACP-048, FACP-049
- Goal id: FACP-G810
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/release/qualification/external_conformance.json, test/formal_assurance/test_facp_058_external_conformance.py
- Predicted files: implementation_plan/formal_assurance_control_plane/release/qualification/external_conformance.json, test/formal_assurance/test_facp_058_external_conformance.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_058_external_conformance.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/external-conformance
- Parallel lane: facp-release-0
- Resource class: cpu-large
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: build/run one independently maintained implementation against public vectors and composition contracts; write sanitized receipt
- Prohibited effects: use generated implementation as independent validator; network interoperability claim without observation; omit failing vectors
- Conflict policy: Own external-conformance receipt/test only; external implementation source is immutable input.
- Preconditions: Canonical-contract gate, repository contracts, and translation safety relation pass.
- Evidence subset: implementation/source/toolchain identity, positive/negative/mutation vectors, canonical bytes/CIDs/errors, assumptions, failures
- Acceptance: Independent implementation passes the full required vector set with matching canonical identity/errors or release remains blocked with exact counterexamples; independence relationship is documented and content-bound.

## FACP-059 Compose one end-to-end proof-carrying workflow

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: terminal-release
- Depends on: FACP-023, FACP-025, FACP-026, FACP-028, FACP-041, FACP-046, FACP-048, FACP-049, FACP-051, FACP-052, FACP-054, FACP-056, FACP-057, FACP-058
- Goal id: FACP-G820
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/release/terminal/composed_workflow.json, test/formal_assurance/test_facp_059_composed_workflow.py
- Predicted files: implementation_plan/formal_assurance_control_plane/release/terminal/composed_workflow.json, test/formal_assurance/test_facp_059_composed_workflow.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_059_composed_workflow.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/composition
- Parallel lane: facp-terminal
- Resource class: portfolio-integration
- Implementation mode: deterministic-first
- Provider authority: proposal-only
- Allowed effects: execute one bounded synthetic SwissKnife-host-Datasets-Accelerate-Kit workflow under reviewed local effects; persist immutable sanitized evidence
- Prohibited effects: real legal filing/payment/private data; unsupported live backend; browser authority; simulation as production; omit failed assumption
- Conflict policy: Sole composition fan-in; consumes exact qualified repository artifacts without editing them.
- Preconditions: Repair/controller, backend cohort, supply chain, docs, and external conformance gates complete; required live local capability is current.
- Evidence subset: canonical request, admission token, translation receipt, observed execution, immutable storage/current-pointer receipt, presentation projection, repository assumption/guarantee discharge, failure/compensation traces
- Acceptance: One trace satisfies every contract and transition invariant end to end; negative trace variants fail at the intended gate; all effects/authority/evidence remain classified; receipt binds exact source forest and no private/secret value.

## FACP-060 Seal the terminal proof-carrying release

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: terminal-release
- Depends on: FACP-059
- Goal id: FACP-G820
- Owning repository: root
- Outputs: implementation_plan/formal_assurance_control_plane/release/terminal/release_manifest.json, test/formal_assurance/test_facp_060_terminal_release.py
- Predicted files: implementation_plan/formal_assurance_control_plane/release/terminal/release_manifest.json, test/formal_assurance/test_facp_060_terminal_release.py
- Validation: python3 -m pytest test/formal_assurance/test_facp_060_terminal_release.py -q
- Board namespace: formal-assurance-control-plane-v1
- Bundle: facp/release/terminal
- Parallel lane: facp-terminal
- Resource class: release-gate
- Implementation mode: deterministic-only
- Provider authority: none
- Allowed effects: verify all exact current evidence; create content-addressed terminal manifest; request authorized signature through existing release boundary
- Prohibited effects: publish/deploy; accept human prose/provider output as proof; waive zero floor; sign with missing/stale/conflicting evidence
- Conflict policy: Sole terminal-manifest owner; all producer receipts are immutable inputs.
- Preconditions: Composed workflow passes and ReleaseAdmissible evaluates true for exact source/dependency/environment/rights/capability closure.
- Evidence subset: source forest, immutable lock, build environment/artifacts, contracts/controller/policies, proofs/tests, live capability receipts, rights, reproducibility/provenance, composed trace, residual risks/human exceptions
- Acceptance: Independent verifier reconstructs manifest identity and every required predicate; all zero floors are zero; signatures bind complete closure; any unresolved right, stale proof/capability, mutable dependency, nonreproducible artifact, simulated evidence, or unsupported claim keeps release nonadmissible.
