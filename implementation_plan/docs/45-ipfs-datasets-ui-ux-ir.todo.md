# UI/UX IR Supervisor Task Board

Board namespace: `ipfs-datasets-ui-ux-ir-v1`
Task prefix: `UIR-`
Task source kind: `legacy-markdown`

This is the reviewed executable projection of
`implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md`. Tasks use
explicit dependencies and narrow file ownership so the
`ipfs_accelerate_py.agent_supervisor` can schedule conflict-free bundles.

Protected operator inputs, never implementation-task outputs:

- `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md`
- `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md`
- `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md`

Program rules:

- Use manual completion with fresh validation evidence.
- Do not edit shared package exports or registries before `UIR-070`.
- Do not edit the existing SwissKnife deontic broker or control-surface
  mediator before `UIR-033`.
- Do not treat UI visibility as authorization, a monitor as proof, a model
  candidate as admitted semantics, or raw sensor data as a canonical event.
- Keep generated bundle/index/graph/state artifacts under
  `data/agent_supervisor/ui_ux_ir/`, outside this reviewed board.

## UIR-001 Freeze the v1 boundary vocabulary and authority contract

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: architecture
- Depends on:
- Goal id: UIR-G010
- Outputs: external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json
- Validation: test -f external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md && python -m json.tool external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/architecture
- Parallel lane: uir-architecture
- Resource class: cpu-small
- Predicted files: external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json
- Interfaces: UIUXIRArchitectureContract@1
- Allow concurrent with:
- Conflict policy: Read existing code and write only the two declared artifacts; do not modify production modules or the three protected planning files.
- Preconditions: The human plan and existing IR/IDL/ORB sources are available for inspection.
- Effects: Freezes ownership boundaries, supported subsets, semantic terms, extension rules, hardware assumptions, authority classes, and hot-file owners.
- Evidence subset: reviewed contract structure and machine-readable vocabulary validation
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 120
- Merge fate: objective/UIR-G010
- Acceptance: Inventory `ir_core` / Intent and Invocation IR / formalization / logic bridges / MCP-IDL / UI profiles / ORB mediation / Meta capabilities; define v1 supported and unsupported semantics; explicitly reject raw-EMG and universal source-recovery claims; identify exclusive owners for schema / exports / registries / broker / mediator / integration fixtures.

## UIR-002 Freeze the MCP-IDL identity interoperability profile

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: identity
- Depends on: UIR-001
- Goal id: UIR-G010
- Outputs: external/ipfs_datasets/docs/architecture/UI_UX_IR_MCP_IDL_IDENTITY.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/mcp_idl_identity_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py
- Validation: cd external/ipfs_datasets && PYTHONPATH=../ipfs_accelerate python -m pytest tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/idl-identity
- Parallel lane: uir-idl-identity
- Resource class: cpu-small
- Predicted files: external/ipfs_datasets/docs/architecture/UI_UX_IR_MCP_IDL_IDENTITY.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/mcp_idl_identity_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py
- Interfaces: MCPIDLIdentityInterop@1
- Allow concurrent with:
- Conflict policy: Freeze and test identity contracts only; do not rewrite existing MCP registries or normalize legacy IDs in place.
- Preconditions: UIR-001 identifies current Python/TypeScript/Go/Rust descriptor shapes and ID profiles.
- Effects: Declares the verified interface identity profile, preserves legacy IDs as typed aliases, publishes canonical descriptor/preimage vectors, and distinguishes interface identity from UIIR identity.
- Evidence subset: real CIDv1 preimage verification, pseudo-CID rejection, legacy disposition, and cross-language vector receipt
- Token class: medium
- Estimated tokens: 7500
- Estimated context tokens: 10000
- Estimated validation seconds: 120
- Merge fate: objective/UIR-G010
- Acceptance: Use the reviewed CIDv1/raw/sha2-256/base32 profile implemented by the accelerator registry as interface authority; bind all identity-affecting descriptor fields; reject stale mutable-cache and mislabeled DAG-PB behavior; never equate `ui_ir_cid`, `interface_cid`, and a legacy alias; record incompatible existing fixtures rather than silently rewriting them.

## UIR-010 Implement the closed UI/UX IR v1 envelope and JSON Schema

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: schema
- Depends on: UIR-001
- Goal id: UIR-G020
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/ui_ux_ir.schema.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_schema.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_schema.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/schema
- Parallel lane: uir-schema
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/ui_ux_ir.schema.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_schema.py
- Interfaces: UIUXIR@1
- Allow concurrent with:
- Conflict policy: Sole owner of `schema.py` and the v1 JSON Schema; import shared IR contracts but edit no shared core or exports.
- Preconditions: UIR-001 vocabulary and extension policy are reviewed.
- Effects: Establishes immutable top-level records, declared collection semantics, exact reference namespaces, and closed wire validation.
- Evidence subset: schema golden and cross-reference test receipt
- Token class: large
- Estimated tokens: 12000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G020
- Acceptance: Define `ui-ux-ir/v1` with source/review bindings / components / layout / behavior / experience / modality / program and formal refs / entry and terminal semantics / namespaced extensions; reject unknown fields / duplicate IDs / dangling references / missing required paths / invalid collection semantics / executable callbacks / mutation-after-construction.

## UIR-011 Add canonical identity exact decoding and deterministic migrations

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: schema
- Depends on: UIR-010
- Goal id: UIR-G020
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/canonicalize.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/decoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/migrations.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_versioning.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_versioning.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/versioning
- Parallel lane: uir-versioning
- Resource class: cpu-small
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/canonicalize.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/decoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/migrations.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_versioning.py
- Interfaces: UIUXIRDecoder@1, UIUXIRIdentity@1
- Allow concurrent with: UIR-012, UIR-013, UIR-014, UIR-015
- Conflict policy: Own only canonicalization, decoding, migrations, and their tests; do not edit schema declarations, leaf models, or registry exports.
- Preconditions: UIR-010 fixes the v1 collection schema and decoder target.
- Effects: Produces deterministic bytes/identity, exact-version decoding, compatibility declarations, migration paths, and source/destination/loss receipts.
- Evidence subset: canonical vectors, unknown-version rejection, and migration receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 120
- Merge fate: objective/UIR-G020
- Acceptance: Canonical identity is independent of optional CID availability; set-like and ordered collections behave as declared; unknown versions and extensions fail closed; migration paths are deterministic, cycle free, explicitly lossy where necessary, and bound to input/output digests.

## UIR-012 Implement semantic components composition and abstract layout

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: semantics
- Depends on: UIR-010
- Goal id: UIR-G021
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/components.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/layout.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/model/test_components_layout.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/model/test_components_layout.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/model-structure
- Parallel lane: uir-model-structure
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/components.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/layout.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/model/test_components_layout.py
- Interfaces: UIComponentGraph@1, UILayoutConstraints@1
- Allow concurrent with: UIR-011, UIR-013, UIR-014, UIR-015
- Conflict policy: Own component/layout leaves only; framework widget names and target pixels remain adapter metadata.
- Preconditions: UIR-010 defines the envelope and stable reference rules.
- Effects: Adds semantic roles/relationships, slots/data/value states, regions, ordering, constraint predicates, design-token refs, adaptation policies, and attention/resource budgets.
- Evidence subset: component graph closure and layout constraint mutation receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G021
- Acceptance: Components and relationships validate without cycles where forbidden; logical reading/focus order is distinct from visual order; responsive predicates use capabilities; required actions/feedback carry preserve/fallback rules; target-specific CSS or executable layout expressions are rejected.

## UIR-013 Implement behavior UX accessibility and localization semantics

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: semantics
- Depends on: UIR-010
- Goal id: UIR-G021
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/behavior.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/experience.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/model/test_behavior_experience.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/model/test_behavior_experience.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/model-behavior
- Parallel lane: uir-model-behavior
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/behavior.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/experience.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/model/test_behavior_experience.py
- Interfaces: UIBehaviorModel@1, UIExperienceContract@1
- Allow concurrent with: UIR-011, UIR-012, UIR-014, UIR-015
- Conflict policy: Own behavior/experience leaves only; reference actions and expressions but do not implement invocation or rendering.
- Preconditions: UIR-010 defines stable IDs and top-level collections.
- Effects: Adds bounded hierarchical/parallel state machines, focus/navigation, guards/effects, timers, result paths, UX tasks, feedback/recovery, accessibility, localization, and cognitive/attention metadata.
- Evidence subset: state/reference closure, trace fixtures, and accessibility/localization structural receipt
- Token class: large
- Estimated tokens: 12000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G021
- Acceptance: Transition priority and joins are deterministic; cancel/retry/undo/rollback/timeout and failure recovery are explicit; accessible names/roles/states/relationships and modality alternatives resolve; message IDs and locale fallbacks validate; arbitrary callbacks and expressions outside the closed grammar are rejected.

## UIR-014 Implement modality capability program-binding and protocol contracts

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: semantics
- Depends on: UIR-010
- Goal id: UIR-G022
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/modality.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/bindings.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/protocols.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_modality_bindings.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_modality_bindings.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/model-bindings
- Parallel lane: uir-model-bindings
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/modality.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/bindings.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/protocols.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_modality_bindings.py
- Interfaces: UIModalityContract@1, UIProgramBinding@1, UIUXIRProtocols@1
- Allow concurrent with: UIR-011, UIR-012, UIR-013, UIR-015
- Conflict policy: Own modality, binding, and backend-neutral protocols only; no device SDK, ORB call, model runtime, or registry edits.
- Preconditions: UIR-010 establishes schema identities and references.
- Effects: Defines abstract inputs/outputs/device profiles, alternatives, confidence/consent requirements, exact MCP-IDL/Intent/Invocation/composite refs, risk/confirmation/rollback/verification metadata, and bounded pipeline ports.
- Evidence subset: modality fallback and non-authorizing binding adversarial receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G022
- Acceptance: Mouse/keyboard/touch, speech, gesture, gaze/head, normalized Neural Band/captouch, agent, display/spatial/audio/haptic/fallback are representable without SDK types; each action has exactly one semantic target; bindings cannot embed code or grant authority; unsupported capabilities and missing alternatives fail explicitly.

## UIR-015 Bind provenance and separate declaration from runtime artifacts

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: provenance
- Depends on: UIR-010
- Goal id: UIR-G022
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/provenance.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_provenance.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_provenance.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/provenance
- Parallel lane: uir-provenance
- Resource class: io-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/provenance.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_provenance.py
- Interfaces: UIUXIRProvenance@1, UIUXIRArtifactChain@1
- Allow concurrent with: UIR-011, UIR-012, UIR-013, UIR-014
- Conflict policy: Adapt `ir_core` provenance/artifact contracts; do not fork canonicalization, manifests, or proof-authority types.
- Preconditions: UIR-010 defines source and derived-artifact references.
- Effects: Binds sources/spans/producers/configs/review/trust and defines separate formalization, reconstruction, projection, observation, decision, invocation, state, and telemetry artifact roles.
- Evidence subset: source-map closure, tamper detection, and identity-separation receipt
- Token class: medium
- Estimated tokens: 7000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G022
- Acceptance: Every grounded node maps to exact sources; inferred nodes are labeled; derived and observational artifacts retain parent identity but do not perturb declaration identity; deterministic versus observational fields are enforced; tampered or unbound artifacts fail closed.

## UIR-020 Define the UI formal ontology cross-view symbols and compiler contracts

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-012, UIR-013, UIR-014, UIR-015
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/ontology.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/contracts.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_ontology.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_ontology.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-ontology
- Parallel lane: uir-formal-ontology
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/ontology.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/contracts.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_ontology.py
- Interfaces: UIFormalOntology@1, UIFormalizationContracts@1
- Allow concurrent with: UIR-030, UIR-031, UIR-032, UIR-050
- Conflict policy: Define UI-specific vocabulary and adapter contracts over `logic.formalization`; do not modify shared formalization or logic-family internals.
- Preconditions: Core semantic model and provenance contracts pass.
- Effects: Establishes stable cross-view symbols, formal view IDs, source mapping, coverage dispositions, unsupported semantics, compiler requests/bounds, and typed artifact shape.
- Evidence subset: ontology uniqueness, cross-view identity, and unsupported-coverage receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: Components / roles / relationships / actions / events / states / actors / devices / capabilities / norms / sources / program refs share stable symbols; every source semantic has one coverage disposition; backend bounds and result authority are explicit.

## UIR-021 Implement the structural FOL and F-logic compiler

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-020
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/flogic.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_flogic.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_flogic.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-flogic
- Parallel lane: uir-formal-flogic
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/flogic.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_flogic.py
- Interfaces: UIFLogicCompiler@1
- Allow concurrent with: UIR-022, UIR-023, UIR-024
- Conflict policy: Own only the FOL/F-logic leaf and test; depend on public `flogic`/formalization contracts and edit no other compiler.
- Preconditions: UIR-020 ontology and source-map contracts pass.
- Effects: Compiles component, role, containment, slot, label, value, data/action binding, actor, device, and capability facts plus structural invariants.
- Evidence subset: deterministic structural formula and semantic-mutation receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: Unique IDs, resolvable labels, required action bindings, role/property constraints, containment, capability requirements, and source maps compile deterministically; unsupported structures stay explicit; mutated components change only expected facts/obligations.

## UIR-022 Implement the event-calculus behavior compiler

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-020
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/event_calculus.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_event_calculus.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_event_calculus.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-event-calculus
- Parallel lane: uir-formal-event-calculus
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/event_calculus.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_event_calculus.py
- Interfaces: UIEventCalculusCompiler@1
- Allow concurrent with: UIR-021, UIR-023, UIR-024
- Conflict policy: Own only the event-calculus leaf and test; adapt public CEC contracts and do not choose among unstable internal AST variants in schema code.
- Preconditions: UIR-020 ontology and behavior source maps pass.
- Effects: Compiles events, fluents, initiates/terminates/holds conditions, state persistence, focus/navigation, lifecycle, timeout, cancel, rollback, result, and feedback traces.
- Evidence subset: event/fluent compilation, bounded trace, and mutation receipt
- Token class: medium
- Estimated tokens: 9000
- Estimated context tokens: 10000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: State transitions and persistence match reviewed traces; entry/exit, timeout, cancellation, failure, rollback, parallel/join, focus, and feedback events retain exact source IDs; ambiguous or unsupported concurrency remains explicit.

## UIR-023 Implement the temporal deontic first-order compiler

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-020
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/tdfol.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_tdfol.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_tdfol.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-tdfol
- Parallel lane: uir-formal-tdfol
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/tdfol.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_tdfol.py
- Interfaces: UITDFOLCompiler@1
- Allow concurrent with: UIR-021, UIR-022, UIR-024
- Conflict policy: Own only the TDFOL leaf and test; use public TDFOL/formalization contracts and preserve exact result authority.
- Preconditions: UIR-020 defines actors, actions, events, state, time, and norm vocabulary.
- Effects: Compiles invariants, temporal guards, permissions, prohibitions, obligations, confirmation/consent, availability, rate/time windows, required feedback, and modality/accessibility rules.
- Evidence subset: TDFOL parse/proof-or-countermodel and deontic mutation receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: Destructive invocation-before-confirmation, policy-denied invocation, disappearing required errors, stale grants, timing, accessibility alternatives, and fallback obligations compile with exact sources; round-trip candidates cannot weaken prohibition or obligation strength.

## UIR-024 Implement the deontic cognitive event-calculus compiler

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-020
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/dcec.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_dcec.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_dcec.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-dcec
- Parallel lane: uir-formal-dcec
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/dcec.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_dcec.py
- Interfaces: UIDCECCompiler@1
- Allow concurrent with: UIR-021, UIR-022, UIR-023
- Conflict policy: Own only the DCEC leaf and test; adapt public CEC contracts and keep cognitive claims distinct from observed facts.
- Preconditions: UIR-020 defines actor, delegation, perception, communication, intent, consent, and program-action symbols.
- Effects: Compiles perception, knowledge, belief, intention, communication, consent, delegation, confirmation, notification, and accountable-agent obligations.
- Evidence subset: DCEC parse/proof-or-countermodel and cognitive mutation receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: An agent action requires valid delegation; observed input is not automatically user intent; material consequences and consent can become knowledge/notification obligations; unknown belief/knowledge remains unknown; every cognitive formula retains source and actor identity.

## UIR-025 Integrate the four formal views with complete coverage

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formalization
- Depends on: UIR-021, UIR-022, UIR-023, UIR-024
- Goal id: UIR-G031
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/compiler.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_compiler.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_compiler.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/formal-integration
- Parallel lane: uir-formal-integration
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/compiler.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_compiler.py
- Interfaces: UIFormalizationCompiler@1, UIFormalizationArtifact@1
- Allow concurrent with: UIR-040, UIR-053, UIR-054
- Conflict policy: Sole owner of the cross-view compiler; consume leaf APIs without rewriting their formulas or importing optional provers eagerly.
- Preconditions: All four leaf compilers pass their golden and mutation suites.
- Effects: Emits one immutable multi-view artifact, cross-view links, source maps, proof obligations, diagnostics, coverage dispositions, backend requests, and explicit unsupported semantics.
- Evidence subset: integrated cross-view identity and complete semantic-coverage receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G031
- Acceptance: No concatenated mixed-logic blob; every source component / state / transition / action / modality / accessibility rule / binding is represented as represented or approximated or unsupported or intentionally non-formal; cross-view symbols agree; optional backend unavailability is typed and never reported as proof.

## UIR-026 Implement semantic decompilation and layered round-trip equivalence

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: roundtrip
- Depends on: UIR-025
- Goal id: UIR-G032
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/decompiler.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/roundtrip.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_roundtrip.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_roundtrip.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/roundtrip
- Parallel lane: uir-roundtrip
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/decompiler.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/roundtrip.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_roundtrip.py
- Interfaces: UIFormalDecompiler@1, UISemanticRoundTrip@1
- Allow concurrent with: UIR-030, UIR-031, UIR-032, UIR-040, UIR-050
- Conflict policy: Own decompiler/round-trip files only; do not claim source-code or pixel reconstruction and do not mutate compiler leaves.
- Preconditions: UIR-025 emits complete typed formalization artifacts and coverage.
- Effects: Reconstructs supported semantics, records ambiguity/unsupported/loss, and evaluates identity, graph, bounded trace, formula, deontic, accessibility, and modality equivalence.
- Evidence subset: reconstruction, non-weakening, graph/trace equivalence, and counterexample receipt
- Token class: large
- Estimated tokens: 12000
- Estimated context tokens: 16000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G032
- Acceptance: Reconstruction never invents sources, grants, components, actions, or device capability; ambiguous inputs produce alternatives/clarification; prohibitions and obligations cannot weaken; accessibility and essential modality coverage survive; source/pixel equality is excluded from the result.

## UIR-027 Implement constrained Intent IDL and formal-to-UI synthesis

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: synthesis
- Depends on: UIR-026, UIR-030, UIR-031
- Goal id: UIR-G032
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/synthesis.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_synthesis.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_synthesis.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/synthesis
- Parallel lane: uir-synthesis
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/synthesis.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize/test_synthesis.py
- Interfaces: UISynthesizer@1
- Allow concurrent with: UIR-033, UIR-034, UIR-056, UIR-060, UIR-061
- Conflict policy: Own synthesis only; learned or retrieved output remains a candidate and optional providers load lazily.
- Preconditions: Round-trip policy plus MCP-IDL and Intent/Invocation adapters pass.
- Effects: Generates bounded UI/UX IR candidates from stable program/interface refs and reviewed constraints, with ambiguity, provenance, confidence, and admission diagnostics.
- Evidence subset: deterministic template synthesis and candidate-admission adversarial receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G032
- Acceptance: A deterministic template baseline works without a model; candidates validate through schema, source, policy, formal coverage, accessibility, and capability gates; missing semantics clarify or fail; no candidate receives proof, policy, delegation, or execution authority from generation alone.

## UIR-030 Implement the MCP-IDL to UI/UX IR source adapter

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration
- Depends on: UIR-002, UIR-011, UIR-014
- Goal id: UIR-G041
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl_identity.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/source_adapters/test_mcp_idl.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/source_adapters/test_mcp_idl.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/adapter-mcp-idl
- Parallel lane: uir-adapter-mcp-idl
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl_identity.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/source_adapters/test_mcp_idl.py
- Interfaces: MCPIDLUIIRAdapter@1
- Allow concurrent with: UIR-020, UIR-026, UIR-031, UIR-032, UIR-040, UIR-050
- Conflict policy: Add a Python adapter and tests only; treat the existing TypeScript IDL as read-only evidence and do not redefine its CID or operation semantics.
- Preconditions: Exact UI IR decoder and program-binding contracts pass.
- Effects: Verifies canonical interface identities through an injected/lazy authority provider, preserves typed legacy aliases, and converts reviewed interface/method/schema/error/event/capability metadata into stable UI program refs, source maps, candidate affordances, and explicit adapter loss.
- Evidence subset: descriptor identity, method/schema mapping, and unsupported-field receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G041
- Acceptance: Preserve and verify the interface CID separately from the UIIR CID with method and schema refs / errors / event streams / compatibility / capability requirements; generate no execution grant; reject pseudo-CIDs / mismatched preimages / mutable identity drift / malformed or unknown descriptor profiles / remote or unbounded schema refs; report UI semantics not derivable from IDL instead of inventing them.

## UIR-031 Implement Intent and Invocation IR adapters

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration
- Depends on: UIR-011, UIR-014
- Goal id: UIR-G041
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/intent_ir.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/source_adapters/test_intent_ir.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/source_adapters/test_intent_ir.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/adapter-intent
- Parallel lane: uir-adapter-intent
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/intent_ir.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/source_adapters/test_intent_ir.py
- Interfaces: IntentUIIRAdapter@1, InvocationUIIRAdapter@1
- Allow concurrent with: UIR-020, UIR-026, UIR-030, UIR-032, UIR-040, UIR-050
- Conflict policy: Add one adapter and test only; reference Intent and Invocation records by stable identity and never copy executable procedure semantics into UI nodes.
- Preconditions: Exact UI IR decoder and program-binding contracts pass.
- Effects: Projects goals/actions/conditions/effects/verification/control flow and governed invocation metadata into source-grounded UI tasks, action refs, state candidates, feedback, and clarification needs.
- Evidence subset: Intent/action/invocation identity and control-flow mapping receipt
- Token class: medium
- Estimated tokens: 8500
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G041
- Acceptance: Preserve actor and delegation / action / arguments / scope / purpose / environment / rollback / verification / conditions / effects / failures / control edges; unsafe or secret-bearing material is referenced or redacted under existing policy; source text cannot become instructions or authority.

## UIR-032 Implement the SwissKnife TypeScript UI/UX IR codec

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration
- Depends on: UIR-002, UIR-011
- Goal id: UIR-G041
- Outputs: swissknife/src/services/mcp/ui-ux-ir-codec.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-codec.test.ts
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/ui-ux-ir-codec.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/typescript-codec
- Parallel lane: uir-typescript-codec
- Resource class: cpu-medium
- Predicted files: swissknife/src/services/mcp/ui-ux-ir-codec.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-codec.test.ts
- Interfaces: UIIRTypeScriptCodec@1
- Allow concurrent with: UIR-020, UIR-026, UIR-030, UIR-031, UIR-034, UIR-040, UIR-050
- Conflict policy: Add new TypeScript files only; do not edit MCP-IDL, UI profile, broker, mediator, service exports, or Python schema.
- Preconditions: UIR-011 publishes canonical wire vectors and exact decoder behavior.
- Effects: Adds exact-version TypeScript decoding, validation, canonicalization, source/loss diagnostics, and conversions for existing UI-profile/deontic projection records.
- Evidence subset: TypeScript canonical vectors and invalid-payload receipt
- Token class: large
- Estimated tokens: 9000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G041
- Acceptance: Match Python field closure, ordering/set semantics, canonical bytes, and error classes on shared fixtures; never introduce TypeScript-only canonical fields; conversion from current SwissKnife profiles retains all mapped semantics and lists every loss.

## UIR-033 Integrate UI/UX IR with the deontic broker and control-surface mediator

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime
- Depends on: UIR-025, UIR-032, UIR-034, UIR-055
- Goal id: UIR-G042
- Outputs: swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/orb-mediation
- Parallel lane: uir-orb-mediation
- Resource class: cpu-medium
- Predicted files: swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts
- Interfaces: UIIRORBBridge@1, ControlSurfaceMediation@1
- Allow concurrent with: UIR-027, UIR-056, UIR-060, UIR-061
- Conflict policy: Sole owner of these existing broker/mediator files for the program; preserve compatibility and do not move policy authority into the renderer.
- Preconditions: Formal view compilation, TypeScript codec, and Python mediation decision semantics are stable.
- Effects: Allows current UI generation/device conformance to consume UIIR projections and routes every candidate action through one fail-closed mediation/invocation path with correlated receipts.
- Evidence subset: spy-executor deny/confirm/defer/rewrite/fallback/allow and receipt-chain evidence
- Token class: large
- Estimated tokens: 11000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G042
- Acceptance: Hidden/enabled presentation never authorizes; policy identity and current real input are mandatory for unary and streaming authorization; every invocation re-evaluates current policy; blocking or missing-policy outcomes never call transport; duplicate correlated inputs call at most once; actor/delegation/UI/action/IDL/policy/state/decision/invocation IDs are retained; existing non-UIIR descriptors remain compatible through explicit adapters.

## UIR-034 Align Python and TypeScript mediation to one fail-closed policy

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime
- Depends on: UIR-055
- Goal id: UIR-G042
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_mediator.py, hallucinate_app/python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py
- Validation: cd hallucinate_app && python -m pytest python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/python-policy-parity
- Parallel lane: uir-python-policy-parity
- Resource class: cpu-proof-solver
- Predicted files: hallucinate_app/python/hallucinate_app/control_surface_mediator.py, hallucinate_app/python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py
- Interfaces: ControlSurfacePolicyParity@1
- Allow concurrent with: UIR-027, UIR-032, UIR-056, UIR-060, UIR-061
- Conflict policy: Sole owner of the Hallucinate Python mediator for this program; preserve its public envelope and receipt compatibility while removing permissive ambiguity.
- Preconditions: Canonical Python mediation outcomes and fail-closed error semantics pass UIR-055.
- Effects: Reconciles no-match, missing-policy, invalid-policy, evaluator-error, low-confidence, and unsupported-context behavior with the reviewed TypeScript/Python decision policy.
- Evidence subset: shared policy vectors and executor-spy parity receipt
- Token class: medium
- Estimated tokens: 7500
- Estimated context tokens: 10000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G042
- Acceptance: No-match and missing/invalid policy cannot allow; every outcome and reason code matches shared vectors; evaluator errors and unknown contexts fail closed; input-sensitive policy sees the actual bounded input; decision and receipt identities remain compatible with existing clients.

## UIR-035 Remove the legacy dynamic-renderer transport and HTML bypass

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: security
- Depends on: UIR-033, UIR-041
- Goal id: UIR-G042
- Outputs: swissknife/web/src/orb-dynamic-app-renderer.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/dynamic-renderer-security
- Parallel lane: uir-dynamic-renderer-security
- Resource class: cpu-large
- Predicted files: swissknife/web/src/orb-dynamic-app-renderer.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts
- Interfaces: UIIRDynamicRendererSecurity@1
- Allow concurrent with: UIR-056, UIR-060, UIR-061
- Conflict policy: Sole owner of the legacy dynamic renderer; retain compatible display behavior while routing actions through the canonical codec/renderer and governed ORB.
- Preconditions: UIIR web renderer and fail-closed ORB integration pass.
- Effects: Replaces untrusted HTML interpolation with escaped semantic rendering and replaces direct HTTP action calls with the policy-mediated ORB path.
- Evidence subset: hostile descriptor/result payload, CSP/escaping, direct-network spy, and governed invocation receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G042
- Acceptance: Script/markup/URL/schema injection fixtures render inert; no descriptor or result field reaches unsafe HTML; all actions use the UIIR action binding and mediated ORB; direct fetch/HTTP bypass is absent or blocked; denial/confirmation/error remains visible and accessible.

## UIR-040 Implement capability negotiation projection solving and loss receipts

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: projection
- Depends on: UIR-012, UIR-013, UIR-014, UIR-020
- Goal id: UIR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/capabilities.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/solver.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/loss.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_solver.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_solver.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/projection-core
- Parallel lane: uir-projection-core
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/capabilities.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/solver.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/loss.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_solver.py
- Interfaces: UIDeviceProfile@1, UIProjectionSolver@1, UIProjectionArtifact@1
- Allow concurrent with: UIR-025, UIR-026, UIR-030, UIR-031, UIR-032, UIR-050
- Conflict policy: Own projection core only; profiles are capability based and target adapters may not add hidden mandatory semantics.
- Preconditions: Component/layout, experience, modality, and formal ontology contracts pass.
- Effects: Negotiates capabilities, solves bounded layout/modality/resource constraints, ranks valid variants, reports unsatisfiable obligations, and emits deterministic projection/loss artifacts.
- Evidence subset: deterministic solver, unsatisfiable core, degradation, and mandatory-semantics receipt
- Token class: large
- Estimated tokens: 11000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G050
- Acceptance: Respect action/text/update/field-of-view/latency/attention/safe-area budgets; never silently omit mandatory action, consent, consequence, error, confirmation, feedback, or accessibility alternative; return explicit fallback or unsatisfiable result; use time/step/memory bounds.

## UIR-041 Implement bounded DOM/ARIA import and web/desktop rendering

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: projection
- Depends on: UIR-032, UIR-040
- Goal id: UIR-G051
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/dom_aria.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/web.py, swissknife/src/services/mcp/ui-ux-ir-web-renderer.ts, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_web.py, swissknife/test/mcp-plus-plus/ui-ux-ir-web-renderer.test.ts
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_web.py -q; npm --prefix swissknife run test:run -- test/mcp-plus-plus/ui-ux-ir-web-renderer.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/target-web
- Parallel lane: uir-target-web
- Resource class: cpu-large
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/dom_aria.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/web.py, swissknife/src/services/mcp/ui-ux-ir-web-renderer.ts, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_web.py, swissknife/test/mcp-plus-plus/ui-ux-ir-web-renderer.test.ts
- Interfaces: DOMARIAUIIRAdapter@1, UIIRWebRenderer@1
- Allow concurrent with: UIR-042, UIR-043, UIR-044, UIR-051, UIR-052
- Conflict policy: Own new web/import files only; support a reviewed DOM/ARIA subset and do not promise arbitrary React/CSS source reconstruction.
- Preconditions: TypeScript codec and projection core pass.
- Effects: Imports semantic DOM/ARIA roles/states/relationships/source spans and renders projection artifacts into deterministic accessible web models.
- Evidence subset: DOM semantic import/export, keyboard/focus, loss, and invalid-source receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G051
- Acceptance: Preserve role/name/value/state/relationships/action/form validation/live feedback/focus order for the supported subset; sanitize and never execute imported markup/scripts; report CSS/framework/source details as retained source metadata or loss; render denial/error/confirmation visibly and accessibly.

## UIR-042 Implement the mobile companion projection adapter

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: projection
- Depends on: UIR-040
- Goal id: UIR-G051
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/mobile.py, mobile/src/orb/uiUxIrMobileAdapter.js, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_mobile.py, mobile/src/orb/__tests__/uiUxIrMobileAdapter.test.js
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_mobile.py -q; npm --prefix mobile test -- --runInBand src/orb/__tests__/uiUxIrMobileAdapter.test.js
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/target-mobile
- Parallel lane: uir-target-mobile
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/mobile.py, mobile/src/orb/uiUxIrMobileAdapter.js, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_mobile.py, mobile/src/orb/__tests__/uiUxIrMobileAdapter.test.js
- Interfaces: UIIRMobileProjection@1, UIIRMobileAdapter@1
- Allow concurrent with: UIR-041, UIR-043, UIR-044, UIR-051, UIR-052
- Conflict policy: Own new mobile adapter files only; use current ORB/session contracts through public shapes and do not embed device policy locally.
- Preconditions: Projection capabilities, loss policy, and canonical interaction bindings pass.
- Effects: Produces mobile card/form/list/navigation/confirmation/fallback models and maps them into the existing React Native companion ORB surface.
- Evidence subset: viewport/touch/accessibility/state/fallback and codec receipt
- Token class: large
- Estimated tokens: 9000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G051
- Acceptance: Touch targets, orientation, safe areas, virtual keyboard, screen reader order, focus restoration, pending/error/confirmation, offline/unavailable, and glasses fallback are explicit; mobile does not become a separate policy owner.

## UIR-043 Implement the Meta-glasses and spatial projection adapter

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: projection
- Depends on: UIR-032, UIR-040
- Goal id: UIR-G051
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/glasses.py, swissknife/src/services/glasses/ui-ux-ir-glasses-adapter.ts, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_glasses.py, swissknife/test/mcp-plus-plus/ui-ux-ir-glasses-adapter.test.ts
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_glasses.py -q; npm --prefix swissknife run test:run -- test/mcp-plus-plus/ui-ux-ir-glasses-adapter.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/target-glasses
- Parallel lane: uir-target-glasses
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/glasses.py, swissknife/src/services/glasses/ui-ux-ir-glasses-adapter.ts, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_glasses.py, swissknife/test/mcp-plus-plus/ui-ux-ir-glasses-adapter.test.ts
- Interfaces: UIIRGlassesProjection@1, UIIRGlassesAdapter@1
- Allow concurrent with: UIR-041, UIR-042, UIR-044, UIR-051, UIR-052
- Conflict policy: Add new adapters over existing glasses profiles/compiler; do not change official-capability assumptions or claim raw EMG/camera/mic capabilities for Web Apps.
- Preconditions: TypeScript codec and projection solver pass; UIR-001 Meta capability matrix is authoritative.
- Effects: Maps UI projections to bounded HUD/cards/actions/audio/mobile fallbacks and existing glasses compiler inputs with exact capability and loss receipts.
- Evidence subset: action/text/update/field-of-view budget, unsupported capability, D-pad mapping, and fallback receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G051
- Acceptance: Respect current DAT versus Web App capability paths; normalized Neural Band/captouch uses Arrow/Enter-style intent input; mandatory semantics that do not fit fall back to mobile/audio or fail; privacy indicators and confirmations survive; no continuous cursor, touch, text-input, or raw-EMG assumption is fabricated.

## UIR-044 Implement voice audio and headless projections

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: projection
- Depends on: UIR-040
- Goal id: UIR-G051
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/voice.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_voice.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_voice.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/target-voice
- Parallel lane: uir-target-voice
- Resource class: cpu-small
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/voice.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/projection/test_voice.py
- Interfaces: UIIRVoiceProjection@1, UIIRHeadlessProjection@1
- Allow concurrent with: UIR-041, UIR-042, UIR-043, UIR-051, UIR-052
- Conflict policy: Own voice/headless projection only; no microphone capture, ASR model, TTS engine, or agent executor belongs here.
- Preconditions: Projection solver and experience/modality contracts pass.
- Effects: Serializes tasks, prompts, choices, summaries, confirmations, progress, results, errors, and recovery into audio/speech and structured agent-readable sequences.
- Evidence subset: dialogue ordering, ambiguity, confirmation, transcript/caption, and fallback receipt
- Token class: medium
- Estimated tokens: 7000
- Estimated context tokens: 10000
- Estimated validation seconds: 120
- Merge fate: objective/UIR-G051
- Acceptance: Preserve accessible names, consequences, choices, cancellation, confirmation, pending/result/error/recovery, transcripts/captions, urgency, and interruption policy; output remains renderer-neutral and reports unavailable audio/display fallback explicitly.

## UIR-050 Define canonical interaction events and conventional input adapters

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: input
- Depends on: UIR-014, UIR-015
- Goal id: UIR-G061
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/events.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/conventional.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_events.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_events.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/input-core
- Parallel lane: uir-input-core
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/events.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/conventional.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_events.py
- Interfaces: UIInteractionEvent@1, ConventionalInputAdapter@1
- Allow concurrent with: UIR-020, UIR-026, UIR-030, UIR-031, UIR-032, UIR-040
- Conflict policy: Sole owner of the canonical event envelope; conventional adapter owns only pointer/keyboard/touch/switch/pen normalization and never decides policy.
- Preconditions: Modality and provenance contracts pass.
- Effects: Defines immutable interaction identity, surface event, semantic target/intent candidates, actor/delegation, confidence/calibration, freshness, consent/purpose, context, raw-evidence ref, and correlation/dedup fields.
- Evidence subset: canonical event, target resolution, stale/invalid/redacted payload, and conventional input receipt
- Token class: large
- Estimated tokens: 9500
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G061
- Acceptance: Raw payload is bounded/redacted and not canonical authority; pointer, keyboard, touch, switch, and pen map to common semantic events; synthetic/agent versus human provenance is explicit; stale, malformed, replayed, or missing-consent events fail before mediation.

## UIR-051 Implement speech and microphone intent normalization

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: input
- Depends on: UIR-050
- Goal id: UIR-G061
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/speech.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_speech_input.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_speech_input.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/input-speech
- Parallel lane: uir-input-speech
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/speech.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_speech_input.py
- Interfaces: SpeechInputAdapter@1
- Allow concurrent with: UIR-041, UIR-042, UIR-043, UIR-044, UIR-052
- Conflict policy: Normalize injected ASR candidates only; do not capture microphone data, load a model eagerly, or infer policy/authority.
- Preconditions: Canonical event envelope and speech capability vocabulary pass.
- Effects: Converts bounded transcript/intent candidates into semantic events with language, confidence, alternatives, wake/consent/freshness, target ambiguity, and redacted audio evidence refs.
- Evidence subset: ASR ambiguity, hostile transcript, consent, language, and high-risk clarification receipt
- Token class: medium
- Estimated tokens: 7000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G061
- Acceptance: Low-confidence or multi-target high-risk commands require clarification; transcripts cannot inject instructions or grants; wake/recording consent and purpose are explicit; raw audio remains outside UIIR; cancel/confirm utterances map to the same state actions as other modalities.

## UIR-052 Implement hand gaze head and Neural Band/captouch normalization

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: input
- Depends on: UIR-050
- Goal id: UIR-G061
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/embodied.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_embodied_input.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_embodied_input.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/input-embodied
- Parallel lane: uir-input-embodied
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/embodied.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_embodied_input.py
- Interfaces: EmbodiedInputAdapter@1, NeuralBandIntentAdapter@1
- Allow concurrent with: UIR-041, UIR-042, UIR-043, UIR-044, UIR-051
- Conflict policy: Normalize injected recognized gestures/pose/D-pad events only; raw video, gaze streams, biometrics, EMG, and SDK objects remain outside the package.
- Preconditions: Canonical event envelope and UIR-001 hardware/source policy pass.
- Effects: Maps recognized hand gesture, gaze dwell, head pose, motion, captouch, and Arrow/Enter-style Neural Band inputs into common target/intention candidates with confidence, calibration, consent, and fallback.
- Evidence subset: gesture ambiguity, dwell/debounce, accidental activation, privacy, unsupported capability, and D-pad mapping receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G061
- Acceptance: Require dwell/debounce/confirmation appropriate to risk; distinguish perception from intention; prevent accidental duplicate activation; express unavailable hand/gaze/neural capability and conventional/mobile fallback; never claim or retain raw EMG or visual sensor data.

## UIR-053 Implement deterministic multimodal fusion and arbitration

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: input
- Depends on: UIR-050, UIR-051, UIR-052
- Goal id: UIR-G061
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/fusion.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_fusion.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_fusion.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/input-fusion
- Parallel lane: uir-input-fusion
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/fusion.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_fusion.py
- Interfaces: UIMultimodalFusion@1
- Allow concurrent with: UIR-025
- Conflict policy: Own fusion only; it may select/clarify a candidate but cannot authorize or invoke it.
- Preconditions: Conventional, speech, and embodied adapters emit the same canonical event contract.
- Effects: Correlates events, deduplicates equivalent actions, resolves target/confidence conflicts under deterministic policy, prioritizes live human input over agent proposals, and emits clarification/cancellation decisions.
- Evidence subset: simultaneous-input, duplicate, conflicting-target, stale, cancellation, and determinism receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G061
- Acceptance: One physical/logical action invokes at most once; human priority does not bypass runtime policy; inconsistent high-impact events clarify; late/stale events cannot override newer state; fusion is order-stable under declared correlation windows and produces an explanation.

## UIR-054 Implement the bounded UI state-machine runtime

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime
- Depends on: UIR-013, UIR-053
- Goal id: UIR-G062
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/state_machine.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_state_machine.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_state_machine.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/state-runtime
- Parallel lane: uir-state-runtime
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/state_machine.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_state_machine.py
- Interfaces: UIStateRuntime@1
- Allow concurrent with: UIR-025
- Conflict policy: Interpret the closed behavior model only; no arbitrary code, transport calls, policy grants, clock ambiguity, or renderer mutation.
- Preconditions: Behavior semantics and fused interaction candidates pass.
- Effects: Evaluates guards, chooses deterministic transitions, stages state-only effects and external-effect requests, handles timers/joins/cancel/rollback, and emits transition candidates without executing programs.
- Evidence subset: generated trace, guard/priority, parallel/join, timeout, rollback, and stale-state receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G062
- Acceptance: Deterministic bounded execution; state version/fencing rejects stale events; external effects remain staged; focus/navigation/confirmation/pending/result/error/recovery transitions match fixtures; nontermination, ambiguous priority, and unsupported expressions fail closed.

## UIR-055 Implement formal-policy mediation and governed invocation requests

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime
- Depends on: UIR-025, UIR-030, UIR-031, UIR-040, UIR-054
- Goal id: UIR-G062
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/mediator.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_mediator.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_mediator.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/runtime-mediator
- Parallel lane: uir-runtime-mediator
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/mediator.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_mediator.py
- Interfaces: UIMediator@1, UIMediationDecision@1
- Allow concurrent with:
- Conflict policy: Own Python mediation only; consume existing policy/formalization/invocation contracts and use executor spies rather than implementing ORB transport.
- Preconditions: Formal views, source adapters, projection requirements, and state runtime are stable.
- Effects: Evaluates candidate transitions/actions against current context and typed formal/runtime policy, returns allow/deny/confirm/defer/rewrite/fallback/rate-limit, and builds governed invocation requests only for allow.
- Evidence subset: all-outcome executor-spy, authority non-substitution, delegation, and fail-closed receipt
- Token class: large
- Estimated tokens: 12000
- Estimated context tokens: 16000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G062
- Acceptance: Blocking / unknown / error outcomes never reach executor; UI state cannot grant permission; agent delegation and human consent are exact; rewrite and fallback changes are explicit; theorem / satisfiability / monitor / policy results stay typed; invocation requests bind declaration / projection / state / event / actor / policy / IDL and Intent / expected effects.

## UIR-056 Implement feedback result mapping immutable receipts and replay

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime
- Depends on: UIR-055
- Goal id: UIR-G062
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/receipts.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_receipts.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_receipts.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/runtime-receipts
- Parallel lane: uir-runtime-receipts
- Resource class: io-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/receipts.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/runtime/test_receipts.py
- Interfaces: UIInteractionReceipt@1, UIReplayTrace@1
- Allow concurrent with: UIR-027, UIR-033, UIR-034, UIR-035, UIR-061
- Conflict policy: Own receipts/replay only; replay validates and reconstructs state but never repeats an external effect.
- Preconditions: Mediation decision and invocation/result mappings are stable.
- Effects: Records projection/event/fusion/state/policy/invocation/result/verification/feedback/fallback lineage, separates deterministic from observational data, validates integrity, and replays transitions side-effect free.
- Evidence subset: receipt-chain integrity, tamper, missing-parent, deterministic replay, and no-effect receipt
- Token class: medium
- Estimated tokens: 8500
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G062
- Acceptance: Every outcome including denial and failure has user-visible feedback metadata and immutable lineage; required verification/rollback/fallback is captured; tampering, missing parents, mismatched identities, or reordered invalid traces fail; replay calls no executor and reproduces the same decision/state disposition.

## UIR-060 Implement accessibility privacy and security validators

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: assurance
- Depends on: UIR-040, UIR-053, UIR-055, UIR-056
- Goal id: UIR-G070
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/accessibility.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/privacy.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/security.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_assurance.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_assurance.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/assurance-policy
- Parallel lane: uir-assurance-policy
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/accessibility.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/privacy.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/security.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_assurance.py
- Interfaces: UIAccessibilityValidator@1, UIPrivacyValidator@1, UISecurityValidator@1
- Allow concurrent with: UIR-027, UIR-033, UIR-034, UIR-035, UIR-061
- Conflict policy: Add deterministic validators only; do not rewrite schema, projection, runtime, policy, or public exports to make fixtures pass.
- Preconditions: Projection, input, mediation, and receipt contracts are stable.
- Effects: Checks names/roles/focus/timing/alternatives/feedback/localization, purpose/consent/minimization/retention/sensitive output, expression/import injection, confused deputy, delegation, stale/replay, and presentation authorization bypass.
- Evidence subset: accessibility equivalence, privacy threat, and authorization/injection adversarial receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G070
- Acceptance: Every essential action/output has a viable alternative or explicit unsatisfied finding; raw sensor/biometric/neural material is absent; consent/purpose/retention are exact; imported text/markup/expressions cannot execute; hidden/enabled states cannot bypass policy; findings use stable severity/reason/source IDs.

## UIR-061 Add property fuzz mutation and bounded model-checking gates

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: assurance
- Depends on: UIR-025, UIR-026, UIR-040, UIR-054, UIR-055
- Goal id: UIR-G070
- Outputs: external/ipfs_datasets/tests/property/logic/ui_ux_ir/test_ui_ux_ir_properties.py, external/ipfs_datasets/tests/property/logic/ui_ux_ir/test_ui_ux_ir_state_model.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/property/logic/ui_ux_ir -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/assurance-properties
- Parallel lane: uir-assurance-properties
- Resource class: cpu-large
- Predicted files: external/ipfs_datasets/tests/property/logic/ui_ux_ir/test_ui_ux_ir_properties.py, external/ipfs_datasets/tests/property/logic/ui_ux_ir/test_ui_ux_ir_state_model.py
- Interfaces: UIIRPropertySuite@1
- Allow concurrent with: UIR-027, UIR-033, UIR-034, UIR-035, UIR-056, UIR-060
- Conflict policy: Tests and generated in-memory cases only; do not edit production implementations in this task.
- Preconditions: Schema, compiler/round-trip, projection, state, and mediator APIs are stable enough to generate bounded cases.
- Effects: Exercises canonical idempotence, decode/encode closure, reference/migration invariants, semantic mutations, projection non-loss, norm non-weakening, state reachability/deadlock, duplicate-event safety, and mediator non-execution properties.
- Evidence subset: seeded property population, minimized counterexamples, mutation score, and bounded state graph receipt
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G070
- Acceptance: Seeds and bounds are recorded; failures minimize to durable fixtures; no required invariant survives only because a generator omits the relevant case; model checking distinguishes bounded evidence from theorem proof; critical mutants in schema, norms, projection, and execution gates are killed.

## UIR-062 Build the cross-language canonical and semantic golden corpus

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: conformance
- Depends on: UIR-002, UIR-026, UIR-032, UIR-040, UIR-050, UIR-056
- Goal id: UIR-G070
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/conformance.py, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/golden_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_conformance.py, swissknife/test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_conformance.py -q; npm --prefix swissknife run test:run -- test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/conformance-golden
- Parallel lane: uir-conformance-golden
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/conformance.py, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/golden_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_conformance.py, swissknife/test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts
- Interfaces: UIIRCrossLanguageParity@1
- Allow concurrent with:
- Conflict policy: Sole owner of the canonical golden corpus; production codecs are read-only and discrepancies become failures or follow-up tasks.
- Preconditions: Python/TypeScript codecs, formal round trip, projection loss, events, and receipts are stable.
- Effects: Implements the language-neutral conformance harness and publishes valid/invalid/migration/formalization/reconstruction/projection/event/decision/receipt vectors with exact canonical bytes, IDs, diagnostics, loss, and semantic expectations.
- Evidence subset: byte-identical Python/TypeScript vectors and semantic parity receipt
- Token class: large
- Estimated tokens: 11000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G070
- Acceptance: Cover empty/minimal/complex documents, ordering/set cases, Unicode/localization, nested/parallel state, every modality/target, unsupported/loss, malformed refs/versions, deontic conflicts, runtime outcomes, and tamper cases; Python and TypeScript agree exactly where specified.

## UIR-069 Finalize the internal package export surfaces

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration
- Depends on: UIR-027, UIR-041, UIR-042, UIR-043, UIR-044, UIR-060, UIR-061, UIR-062
- Goal id: UIR-G080
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/__init__.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_internal_api.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_internal_api.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/internal-package-exports
- Parallel lane: uir-public-integration
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/__init__.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_internal_api.py
- Interfaces: UIUXIRInternalPackages@1
- Allow concurrent with:
- Conflict policy: Sole owner of internal subpackage initializers; expose reviewed stable module-local APIs lazily and do not edit root exports, shared registries, production leaves, or protected plans.
- Preconditions: Core, formal, source, projection, runtime, assurance, and conformance modules pass through their direct tests.
- Effects: Creates deterministic lazy internal package surfaces without optional-provider side effects or accidental exports of backend-private AST/runtime types.
- Evidence subset: internal import closure, lazy optional dependency, and stable symbol receipt
- Token class: medium
- Estimated tokens: 6500
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G080
- Acceptance: Every internal package imports offline and exposes only reviewed symbols; optional solvers / browsers / models / devices remain lazy; imports create no process / network / hardware action; backend-private logic types do not become UIIR public contracts.

## UIR-070 Publish the public API and register the schema and bridge

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration
- Depends on: UIR-033, UIR-034, UIR-035, UIR-069
- Goal id: UIR-G080
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/api.py, external/ipfs_datasets/ipfs_datasets_py/logic/submodule_registry.py, external/ipfs_datasets/ipfs_datasets_py/logic/bridge/registry.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_public_api.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_public_api.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/public-integration
- Parallel lane: uir-public-integration
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/api.py, external/ipfs_datasets/ipfs_datasets_py/logic/submodule_registry.py, external/ipfs_datasets/ipfs_datasets_py/logic/bridge/registry.py, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_public_api.py
- Interfaces: UIUXIRPublicAPI@1, UIUXIRBridgeRegistration@1
- Allow concurrent with:
- Conflict policy: Sole late owner of all shared exports and registries; preserve existing APIs, lazy imports, registry order, and compatibility aliases.
- Preconditions: Internal package exports and all ORB/policy/renderer integration gates pass.
- Effects: Exposes the reviewed small API, registers `ui-ux-ir/v1`, advertises submodule capabilities, and registers the UI formalization bridge without importing optional runtimes eagerly.
- Evidence subset: cold import, public symbol, schema registry, bridge manifest, and compatibility receipt
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G080
- Acceptance: Cold import starts no process/network/model/browser/device action; only intentional stable symbols are exported; schema and bridge registrations resolve deterministically; existing logic API and submodule tests remain green; no private logic-family internal becomes a new public dependency.

## UIR-071 Build the responsive web and mobile form pilot

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: pilots
- Depends on: UIR-041, UIR-042, UIR-055, UIR-056, UIR-060, UIR-070
- Goal id: UIR-G081
- Outputs: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/responsive_form.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_responsive_form_pilot.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/ui_ux_ir/test_responsive_form_pilot.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/pilot-form
- Parallel lane: uir-pilot-form
- Resource class: cpu-large
- Predicted files: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/responsive_form.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_responsive_form_pilot.py
- Interfaces: ResponsiveFormPilot@1
- Allow concurrent with: UIR-072, UIR-073, UIR-074
- Conflict policy: Own only the form fixture and test; use public APIs and target adapters rather than private internals.
- Preconditions: Public API, web/mobile projections, runtime mediator/receipts, and assurance validators pass.
- Effects: Exercises schema-derived fields/validation, responsive layout, keyboard/touch, accessibility/localization, submit/cancel/error/retry, web/mobile projection loss, and governed submission.
- Evidence subset: cross-target semantic equivalence and complete interaction receipt chain
- Token class: medium
- Estimated tokens: 7000
- Estimated context tokens: 10000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G081
- Acceptance: Web and mobile preserve the same fields, validation, accessible relationships, actions, states, errors, and results; target layout differs only under declared adaptation; invalid and denied submissions do not execute; replay reproduces state and feedback.

## UIR-072 Build the destructive confirmation rollback and recovery pilot

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pilots
- Depends on: UIR-041, UIR-055, UIR-056, UIR-060, UIR-070
- Goal id: UIR-G081
- Outputs: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/destructive_workflow.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_destructive_workflow_pilot.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/ui_ux_ir/test_destructive_workflow_pilot.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/pilot-destructive
- Parallel lane: uir-pilot-destructive
- Resource class: cpu-proof-solver
- Predicted files: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/destructive_workflow.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_destructive_workflow_pilot.py
- Interfaces: DestructiveWorkflowPilot@1
- Allow concurrent with: UIR-071, UIR-073, UIR-074
- Conflict policy: Own only the destructive fixture/test and use an executor spy; no real destructive external action.
- Preconditions: Public API, web projection, formal-policy mediator, receipts, and assurance pass.
- Effects: Exercises consequence preview / user knowledge and consent / confirmation obligation / cancel / timeout / stale confirmation / deny / allowed invocation / partial failure / verification / rollback and compensation / feedback / replay.
- Evidence subset: TDFOL/DCEC non-bypass, executor-spy, rollback, and receipt evidence
- Token class: medium
- Estimated tokens: 8000
- Estimated context tokens: 10000
- Estimated validation seconds: 600
- Merge fate: objective/UIR-G081
- Acceptance: No invocation before current explicit confirmation; hidden control or agent proposal cannot bypass; stale/different-action confirmation is rejected; failure and rollback are perceivable; every decision/effect/result/feedback is source and identity bound.

## UIR-073 Build the Meta-glasses multimodal and mobile-fallback pilot

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pilots
- Depends on: UIR-043, UIR-052, UIR-055, UIR-056, UIR-060, UIR-070
- Goal id: UIR-G081
- Outputs: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/meta_glasses.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_meta_glasses_pilot.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/ui_ux_ir/test_meta_glasses_pilot.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/pilot-glasses
- Parallel lane: uir-pilot-glasses
- Resource class: cpu-large
- Predicted files: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/meta_glasses.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_meta_glasses_pilot.py
- Interfaces: MetaGlassesUIIRPilot@1
- Allow concurrent with: UIR-071, UIR-072, UIR-074
- Conflict policy: Hardware-free fixture/test only; current documented capability matrix is authoritative and raw EMG/video/audio is never retained.
- Preconditions: Glasses projection, embodied input, mediator/receipts, assurance, and public API pass.
- Effects: Exercises bounded HUD actions/text, D-pad/Arrow/Enter-style Neural Band/captouch intents, ambiguity/debounce, denied and confirmation states, unavailable capabilities, audio/mobile fallback, disconnect/reconnect, privacy, and replay.
- Evidence subset: glasses projection/loss, normalized input, fallback, privacy, and end-to-end receipt evidence
- Token class: medium
- Estimated tokens: 8500
- Estimated context tokens: 10000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G081
- Acceptance: No fabricated cursor/touch/text/raw-EMG capability; mandatory content that does not fit moves to an explicit mobile/audio fallback; accidental/duplicate gestures invoke at most once; high-risk action confirms; disconnect/stale state fails safely with user-visible recovery.

## UIR-074 Build the dynamic program and Agent Supervisor UI pilot

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: pilots
- Depends on: UIR-027, UIR-030, UIR-031, UIR-041, UIR-055, UIR-056, UIR-070
- Goal id: UIR-G081
- Outputs: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/agent_supervisor_program.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_program_supervisor_pilot.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/ui_ux_ir/test_program_supervisor_pilot.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/pilot-program
- Parallel lane: uir-pilot-program
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots/agent_supervisor_program.json, external/ipfs_datasets/tests/integration/logic/ui_ux_ir/test_program_supervisor_pilot.py
- Interfaces: ProgramSupervisorUIIRPilot@1
- Allow concurrent with: UIR-071, UIR-072, UIR-073
- Conflict policy: Fixture/test only; use stable mocked MCP-IDL and Intent/Invocation contracts and do not mutate real supervisor queues or goals.
- Preconditions: Synthesis, adapters, web projection, mediator/receipts, and public API pass.
- Effects: Synthesizes goal/task/status/detail/actions UI from program/IDL/Intent contracts and exercises refresh, select, propose, confirm, pause/cancel denial, delegated agent proposal, progress/result/error, and receipt links.
- Evidence subset: synthesis provenance, program binding, delegation/policy, dynamic state, and receipt evidence
- Token class: medium
- Estimated tokens: 8500
- Estimated context tokens: 10000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G081
- Acceptance: Dynamic UI changes follow declared program state and capability only; task/goal data cannot inject code/instructions; agent proposals remain visibly distinct and delegation bounded; governed actions mediate and confirm; UI state never fabricates supervisor completion or authority.

## UIR-080 Add UI/UX IR scale latency and resource benchmarks

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: performance
- Depends on: UIR-071, UIR-072, UIR-073, UIR-074
- Goal id: UIR-G090
- Outputs: external/ipfs_datasets/tests/benchmarks/test_ui_ux_ir_performance.py, external/ipfs_datasets/docs/benchmarks/ui_ux_ir_performance_policy.json
- Validation: cd external/ipfs_datasets && python -m pytest tests/benchmarks/test_ui_ux_ir_performance.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/performance
- Parallel lane: uir-performance
- Resource class: cpu-large
- Predicted files: external/ipfs_datasets/tests/benchmarks/test_ui_ux_ir_performance.py, external/ipfs_datasets/docs/benchmarks/ui_ux_ir_performance_policy.json
- Interfaces: UIUXIRBenchmark@1
- Allow concurrent with: UIR-081, UIR-082
- Conflict policy: Benchmark/tests and reviewed policy only; do not weaken semantics or rewrite production code to hide regressions.
- Preconditions: Four pilots define representative documents/traces and public API is stable.
- Effects: Measures decode/validate/canonicalize/formalize/project/mediate/replay latency, memory, output size, graph/state complexity, and timeout behavior across bounded fixture sizes.
- Evidence subset: benchmark population, environment, thresholds, distributions, and timeout/resource receipt
- Token class: medium
- Estimated tokens: 7000
- Estimated context tokens: 10000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G090
- Acceptance: Verify documented 1k/10k-node and 10 MiB bounds or replace provisional targets with reviewed measured thresholds; all external solver/model/browser/device calls declare time/output limits; performance failures remain failures rather than semantic shortcuts.

## UIR-081 Run hardware-free browser mobile and Meta-glasses E2E replay

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: e2e
- Depends on: UIR-062, UIR-071, UIR-072, UIR-073, UIR-074
- Goal id: UIR-G090
- Outputs: swissknife/test/e2e/ui-ux-ir-pilots.spec.ts, swissknife/build-tools/configs/playwright.ui-ux-ir.config.ts, mobile/src/orb/__tests__/uiUxIrPilotReplay.test.js
- Validation: cd swissknife && node scripts/run-with-owned-port.mjs --env-var SWISSKNIFE_UI_UX_IR_E2E_PORT --preferred 3001 -- node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.ui-ux-ir.config.ts; npm --prefix mobile test -- --runInBand src/orb/__tests__/uiUxIrPilotReplay.test.js
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/e2e
- Parallel lane: uir-e2e
- Resource class: cpu-large
- Predicted files: swissknife/test/e2e/ui-ux-ir-pilots.spec.ts, swissknife/build-tools/configs/playwright.ui-ux-ir.config.ts, mobile/src/orb/__tests__/uiUxIrPilotReplay.test.js
- Interfaces: UIUXIRE2E@1
- Allow concurrent with: UIR-080
- Conflict policy: Add E2E/replay tests and a dedicated test config only; use owned ports and deterministic mocks and do not modify production adapters or shared Playwright configs in this task.
- Preconditions: Cross-language corpus and all four pilot contract tests pass.
- Effects: Runs browser/desktop, mobile companion, and glasses simulator paths across positive, denial, confirmation, ambiguity, disconnect, unsupported, fallback, failure, rollback, and replay cases.
- Evidence subset: browser console/network, mobile state, glasses handoff, policy/invocation/feedback, and replay receipts
- Token class: large
- Estimated tokens: 10000
- Estimated context tokens: 16000
- Estimated validation seconds: 900
- Merge fate: objective/UIR-G090
- Acceptance: No console/runtime errors; visible/accessibility states match decisions; blocking outcomes produce zero transport calls; mobile/glasses fallback works; cross-target semantic IDs correlate; mocks declare capability limits; all traces and artifacts bind exact fixture/code identities.

## UIR-082 Publish the UI/UX IR API extension and migration guide

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: documentation
- Depends on: UIR-070, UIR-081
- Goal id: UIR-G090
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/README.md, external/ipfs_datasets/docs/logic/UI_UX_IR_GUIDE.md, external/ipfs_datasets/tests/documentation/test_ui_ux_ir_docs.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/documentation/test_ui_ux_ir_docs.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/documentation
- Parallel lane: uir-documentation
- Resource class: cpu-small
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/README.md, external/ipfs_datasets/docs/logic/UI_UX_IR_GUIDE.md, external/ipfs_datasets/tests/documentation/test_ui_ux_ir_docs.py
- Interfaces: UIUXIRDocumentation@1
- Allow concurrent with: UIR-080
- Conflict policy: Documentation and link/API example tests only; describe current public behavior and retain explicit limitations.
- Preconditions: Public API and hardware-free E2E behavior are stable.
- Effects: Documents mental model / schema / APIs / formal views / round trips / synthesis / target and input adapters / ORB boundary / safety / extensions / migrations / examples / limitations / operator troubleshooting.
- Evidence subset: tested code examples, API symbol links, schema/version links, and capability-claim audit
- Token class: medium
- Estimated tokens: 6500
- Estimated context tokens: 10000
- Estimated validation seconds: 120
- Merge fate: objective/UIR-G090
- Acceptance: Examples use public imports and run offline; clearly distinguish declaration/projection/runtime/proof authority; explain semantic rather than pixel/source round trip; document Meta DAT/Web App and Neural Band limits; show safe extension and migration patterns without weakening closed-core validation.

## UIR-083 Add the root current-tree conformance and release gate

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: release
- Depends on: UIR-061, UIR-062, UIR-080, UIR-081, UIR-082
- Goal id: UIR-G090
- Outputs: external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/test_ui_ux_ir_conformance.py -q
- Board namespace: ipfs-datasets-ui-ux-ir-v1
- Bundle: ui-ux-ir/release
- Parallel lane: uir-release
- Resource class: cpu-medium
- Predicted files: external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py
- Interfaces: UIUXIRReleaseGate@1
- Allow concurrent with:
- Conflict policy: Final single owner of the root gate; aggregate evidence without modifying producers, fixtures, thresholds, boards, or objective status.
- Preconditions: Property/model, golden parity, benchmarks, E2E, and documentation gates have current-tree receipts.
- Effects: Verifies exact superproject/submodule identities, selected test populations, child-goal evidence, artifact integrity/freshness, unresolved findings, capability policy, and release invariants in one fail-closed receipt.
- Evidence subset: complete child receipt ledger and root conformance receipt
- Token class: large
- Estimated tokens: 9000
- Estimated context tokens: 16000
- Estimated validation seconds: 300
- Merge fate: objective/UIR-G090
- Acceptance: Enumerate every goal/task producer and current receipt; reject stale/missing/contradictory evidence, skipped mandatory populations, authority substitution, unresolved P0/P1 loss/security/privacy/accessibility findings, or dirty identity mismatch; passing this gate is necessary but objective status changes remain under the supervisor completion policy.
