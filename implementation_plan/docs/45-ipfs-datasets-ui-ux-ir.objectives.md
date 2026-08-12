# UI/UX IR Objective Heap

This file is the durable source of intent for the `ipfs_datasets_py.logic`
UI/UX intermediate-representation program. The companion executable projection
is `implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md` with task
prefix `## UIR-`. The human architecture and rollout plan is
`implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md`.

The objective heap is authoritative; todo status, generated text, source-file
existence, and model output do not prove completion. A goal may close only from
fresh validation evidence bound to the current repository and submodule trees.

## Goal tree

```text
UIR-G000  Bidirectional logic-grounded UI/UX IR
|-- UIR-G010  Reviewed boundary and supported-subset contract
|-- UIR-G020  Canonical immutable UI/UX IR v1
|   |-- UIR-G021  Component, layout, behavior, and experience semantics
|   `-- UIR-G022  Modality, program binding, and provenance semantics
|-- UIR-G030  Multi-view formal semantics and semantic round trip
|   |-- UIR-G031  FOL/F-logic, event calculus, TDFOL, and DCEC compilers
|   `-- UIR-G032  Decompilation, equivalence, and constrained synthesis
|-- UIR-G040  MCP-IDL, Intent IR, TypeScript, and ORB integration
|   |-- UIR-G041  Source adapters and cross-language codec
|   `-- UIR-G042  Runtime ORB and control-surface mediation
|-- UIR-G050  Capability-constrained target projection
|   `-- UIR-G051  Web, mobile, glasses, and voice/headless adapters
|-- UIR-G060  Multimodal runtime and program orchestration
|   |-- UIR-G061  Input normalization and multimodal fusion
|   `-- UIR-G062  State, policy, invocation, feedback, and receipts
|-- UIR-G070  Accessibility, privacy, security, and conformance assurance
|-- UIR-G080  Public integration and vertical pilots
|   `-- UIR-G081  Cross-target form, destructive flow, glasses, and program pilots
`-- UIR-G090  Performance, E2E evidence, documentation, and release closure
```

## UIR-G000 Bidirectional logic-grounded UI/UX IR

- Status: active
- Parent:
- Fib priority: 1
- Track: ui-ux-ir
- Priority: P0
- Bundle: ui-ux-ir/root
- Parallel lane: integration-release
- Resource class: cpu-medium
- Goal: Deliver a source-grounded, content-addressed UI/UX intermediate representation that translates supported UI semantics to and from linked formal-logic views, synthesizes and projects safe adaptive interfaces, and orchestrates multimodal input through governed program and ORB invocations.
- Evidence: 941000000000000000000
- Evidence criteria: 941000000000000000000=every child goal has a fresh terminal validation receipt bound to the current superproject, ipfs_datasets, and SwissKnife trees; canonical identity, formal coverage, semantic round-trip, target projection, runtime mediation, accessibility, privacy, adversarial, cross-language, simulator, and performance gates all pass without authority substitution or silent loss.
- Evidence source policy: A qualifying root receipt must enumerate every child receipt and exact tree identity, include the selected test populations and benchmark policy, and report zero unresolved P0/P1 semantic-loss, authorization-bypass, privacy, accessibility, cross-language, or unsupported-capability findings. This heap, the plan, generated tasks, source existence, model output, and similarity scores are non-qualifying.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir, external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py, implementation_plan/docs/45-ipfs-datasets-ui-ux-ir-plan-2026-07-31.md, implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.objectives.md, implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir, external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py
- Interfaces: UIUXIR@1, UIFormalization@1, UIProjection@1, UIRuntimeMediation@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/test_ui_ux_ir_conformance.py -q
- Acceptance: Supported UI declarations round trip through canonical UI/UX IR and typed FOL/F-logic, event-calculus, TDFOL, and DCEC views under the reviewed equivalence policy; desktop, mobile, glasses, and voice/headless projections preserve mandatory semantics or fail with explicit loss; all external effects remain runtime-authorized and receipted; the four reference pilots and release gates pass.
- Gap task: Close the highest-priority uncovered child without weakening content identity, source grounding, formal result authority, authorization, accessibility, privacy, or explicit-loss policy.
- Refinement: Implement exclusive leaf files in parallel; reserve shared exports, registries, existing broker/mediator edits, integration fixtures, and release state for late single-owner tasks.
- Embedding query: UI UX intermediate representation bidirectional formal logic frame logic temporal deontic event calculus DCEC multimodal adaptive interface program orchestration
- AST query: UIIRDocument UIFormalizationArtifact UIProjectionArtifact UIInteractionEvent UIMediationDecision SemanticRoundTripReport

## UIR-G010 Reviewed boundary and supported-subset contract

- Status: active
- Parent: UIR-G000
- Fib priority: 1
- Track: architecture
- Priority: P0
- Bundle: ui-ux-ir/architecture
- Parallel lane: uir-architecture
- Resource class: cpu-small
- Goal: Freeze the UI/UX IR ownership boundary, v1 semantic vocabulary, supported import/projection subsets, result-authority policy, hardware assumptions, and implementation conflict map before schema implementation.
- Evidence: 941000000000000000010
- Evidence criteria: 941000000000000000010=a reviewed architecture contract and machine-readable vocabulary inventory enumerate retained existing authorities, supported and unsupported semantics, exact Meta capability assumptions, extension policy, threat boundaries, and exclusive shared-file ownership.
- Evidence source policy: Only a reviewed contract plus a fresh structural validation receipt qualifies; this objective text and unreviewed generated documentation do not.
- Outputs: external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md, external/ipfs_datasets/docs/architecture/UI_UX_IR_MCP_IDL_IDENTITY.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/mcp_idl_identity_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py
- Predicted files: external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md, external/ipfs_datasets/docs/architecture/UI_UX_IR_MCP_IDL_IDENTITY.md, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/mcp_idl_identity_vectors.json, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py
- Interfaces: UIUXIRArchitectureContract@1, MCPIDLIdentityInterop@1
- Validation: test -f external/ipfs_datasets/docs/architecture/UI_UX_IR_CONTRACT.md && python -m json.tool external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/vocabulary.json; cd external/ipfs_datasets && PYTHONPATH=../ipfs_accelerate python -m pytest tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py -q
- Acceptance: The contract distinguishes UI declaration, Intent/program semantics, IDL operation contracts, formal views, projections, observations, mediation, and proof authority; the identity profile distinguishes verified `interface_cid`, `ui_ir_cid`, and typed legacy aliases and rejects pseudo-CIDs or mismatched preimages; no raw Neural Band/EMG or universal source-recovery claim is made; all hot shared files have one late owner.
- Gap task: Resolve the smallest missing boundary, vocabulary, source-authority, or conflict-ownership decision without writing production code.
- Refinement: Keep this task read-only with respect to current production modules and do not expand the v1 subset from speculation.
- Embedding query: UI IR architecture supported subset semantic vocabulary authority boundary Meta Neural Band capability conflict ownership
- AST query: IntentIRDocument InvocationIntentEnvelope InterfaceDescriptor FormalizationArtifact AuthorityKind

## UIR-G020 Canonical immutable UI/UX IR v1

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G010
- Fib priority: 2
- Track: schema
- Priority: P0
- Bundle: ui-ux-ir/core
- Parallel lane: uir-core-integration
- Resource class: cpu-medium
- Goal: Define and implement the closed `ui-ux-ir/v1` declaration, exact decoder, deterministic identity, migration, cross-reference, provenance, and artifact contracts on the shared IR kernel.
- Evidence: 941000000000000000020
- Evidence criteria: 941000000000000000020=fresh tests prove canonical bytes and identity, declared collection semantics, exact versioning, immutable construction, complete cross-reference checks, deterministic migrations and loss receipts, source maps, and separation of declaration from derived/runtime artifacts.
- Evidence source policy: A complete unit-test receipt over schema, decoder, canonical vectors, mutations, migrations, and provenance qualifies. Source existence or a JSON Schema validation alone does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/ui_ux_ir.schema.json, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/canonicalize.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/decoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/migrations.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/provenance.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/schema.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/ui_ux_ir.schema.json, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/canonicalize.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/decoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/migrations.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/provenance.py
- Interfaces: UIUXIR@1, UIUXIRDecoder@1, UIUXIRIdentity@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_schema.py tests/unit/logic/ui_ux_ir/test_versioning.py tests/unit/logic/ui_ux_ir/test_provenance.py -q
- Acceptance: Unknown versions and extensions fail closed; all references and entry/terminal requirements validate; immutable declarations retain stable identity regardless of projection, proof, runtime, or telemetry artifacts; legacy migration is explicit and reversible where declared.
- Gap task: Implement the smallest missing v1 schema, decoding, identity, migration, or provenance contract with canonical and adversarial fixtures.
- Refinement: Give the schema, model leaves, decoder/migration, and provenance files exclusive owners; do not edit package exports or registries.
- Embedding query: UI UX IR v1 immutable schema canonical JSON CID provenance decoder migration cross reference
- AST query: UIIRDocument decode_ui_ir canonicalize_ui_ir UIIRValidationError MigrationReceipt

## UIR-G021 Component layout behavior and experience semantics

- Status: active
- Parent: UIR-G020
- Depends on: UIR-G010
- Fib priority: 2
- Track: semantics
- Priority: P0
- Bundle: ui-ux-ir/model
- Parallel lane: uir-model
- Resource class: cpu-medium
- Goal: Model semantic components, composition, abstract layout, design intent, state machines, UX tasks, accessibility, localization, feedback, recovery, and attention constraints without framework-specific executable code.
- Evidence: 941000000000000000021
- Evidence criteria: 941000000000000000021=reviewed fixtures and mutation tests cover component/reference closure, layout constraints, state/control flow, focus/navigation, accessibility relationships, localization, feedback, failure/recovery, parallel joins, and forbidden executable expressions.
- Evidence source policy: Fresh model conformance and semantic-mutation receipts qualify; visual screenshots or source-code type checks alone do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/components.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/layout.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/behavior.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/experience.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/components.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/layout.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/behavior.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/experience.py
- Interfaces: UIComponentGraph@1, UILayoutConstraints@1, UIBehaviorModel@1, UIExperienceContract@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/model -q
- Acceptance: The model expresses the reviewed supported subset, separates logical from visual/focus order, makes essential feedback and recovery explicit, supports bounded hierarchical/parallel state regions, and rejects callbacks, arbitrary code, dangling relationships, and ambiguous transition priority.
- Gap task: Add one missing semantic leaf and its exclusive unit fixtures without changing shared schema ownership.
- Refinement: Components/layout and behavior/experience may run as separate task lanes after the envelope contract lands.
- Embedding query: semantic UI component graph layout constraints state machine UX flow accessibility localization feedback recovery attention
- AST query: UIComponent LayoutConstraint UIState UITransition UXTask AccessibilityContract LocalizationBinding

## UIR-G022 Modality program binding and provenance semantics

- Status: active
- Parent: UIR-G020
- Depends on: UIR-G010
- Fib priority: 2
- Track: semantics
- Priority: P0
- Bundle: ui-ux-ir/bindings
- Parallel lane: uir-bindings
- Resource class: cpu-medium
- Goal: Define abstract input/output capabilities, alternatives, device requirements, data bindings, MCP-IDL and Intent/Invocation references, formal-constraint links, risk/confirmation metadata, and immutable artifact lineage.
- Evidence: 941000000000000000022
- Evidence criteria: 941000000000000000022=fixtures prove capability and fallback closure, one semantic action target per binding, schema/CID/source resolution, non-authorizing UI bindings, actor/delegation and risk metadata, sensor minimization, and declaration-versus-runtime identity separation.
- Evidence source policy: Fresh binding, modality, provenance, and authority-adversarial test receipts qualify. A renderer demo or successful ORB call alone does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/modality.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/bindings.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/protocols.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/modality.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/bindings.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/protocols.py
- Interfaces: UIModalityContract@1, UIProgramBinding@1, UIUXIRProtocols@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_modality.py tests/unit/logic/ui_ux_ir/test_bindings.py tests/unit/logic/ui_ux_ir/test_protocols.py -q
- Acceptance: Pointer, keyboard, touch, speech, gesture, gaze/head, normalized Neural Band/captouch, agent, display, spatial, audio, haptic, and fallback capabilities are representable without device SDK types; program bindings reference existing authorities and never embed code or grants.
- Gap task: Implement one missing capability, binding, or protocol contract with failure fixtures.
- Refinement: Keep modality, bindings, and protocol files independent and defer existing API/registry edits.
- Embedding query: UI modality device capability fallback MCP IDL Intent IR invocation binding provenance risk confirmation
- AST query: InputCapability OutputCapability DeviceProfile UIActionBinding UIProgramRef UIFormalConstraintRef

## UIR-G030 Multi-view formal semantics and semantic round trip

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G020, UIR-G021, UIR-G022
- Fib priority: 3
- Track: formalization
- Priority: P0
- Bundle: ui-ux-ir/formalization
- Parallel lane: uir-formal-integration
- Resource class: cpu-proof-solver
- Goal: Compile UI/UX IR into source-mapped linked formal views, reconstruct supported semantics, and evaluate layered semantic equivalence without conflating validation, satisfiability, monitoring, policy approval, or theorem proof.
- Evidence: 941000000000000000030
- Evidence criteria: 941000000000000000030=fresh compiler, decompiler, cross-view coverage, mutation, counterexample, and round-trip receipts cover every reviewed semantic family and preserve explicit unsupported/loss dispositions and exact result authority.
- Evidence source policy: Deterministic formalization/reconstruction receipts plus applicable backend proof or countermodel evidence qualify. Parser success, model-generated formulas, or a policy allow decision cannot substitute.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/formalize
- Interfaces: UIFormalization@1, UIReconstruction@1, UISemanticRoundTrip@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize -q
- Acceptance: Structural, behavioral, temporal/deontic, cognitive/delegation, and accessibility semantics map to typed linked views; every source node has a coverage disposition; reconstruction cannot broaden authority or weaken norms; supported round trips meet the reviewed equivalence policy.
- Gap task: Close the smallest missing formal view, cross-view link, reconstruction rule, or equivalence gate with a grounded counterexample fixture.
- Refinement: Run logic-family compilers in exclusive leaves; integrate cross-view compilation once leaves pass; decompilation and synthesis remain separate from theorem backends.
- Embedding query: UI formalization multi view F logic event calculus TDFOL DCEC decompiler semantic round trip equivalence
- AST query: UIFormalizationArtifact FormalizationView CrossViewLink UIReconstructionArtifact SemanticRoundTripReport

## UIR-G031 FOL F-logic event calculus TDFOL and DCEC compilers

- Status: active
- Parent: UIR-G030
- Depends on: UIR-G020, UIR-G021, UIR-G022
- Fib priority: 3
- Track: formalization
- Priority: P0
- Bundle: ui-ux-ir/logic-compilers
- Parallel lane: uir-logic-compilers
- Resource class: cpu-proof-solver
- Goal: Implement source-mapped compiler leaves for structural FOL/F-logic, behavioral event calculus, temporal-deontic first-order logic, and deontic cognitive event calculus, then join them through one coverage-aware UI formalization artifact.
- Evidence: 941000000000000000031
- Evidence criteria: 941000000000000000031=each compiler passes deterministic golden and semantic-mutation tests, emits typed symbols/formulas/source maps/diagnostics, uses public logic contracts, and the integrated artifact reports complete represented/approximated/unsupported/non-formal coverage.
- Evidence source policy: Fresh compiler fixtures and applicable parser/prover/countermodel receipts qualify per view. Cross-family string concatenation or deep coupling to unstable internal AST classes does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/contracts.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/ontology.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/flogic.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/event_calculus.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/tdfol.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/dcec.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/compiler.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/contracts.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/ontology.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/flogic.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/event_calculus.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/tdfol.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/dcec.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/compiler.py
- Interfaces: UIFLogicCompiler@1, UIEventCalculusCompiler@1, UITDFOLCompiler@1, UIDCECCompiler@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_flogic.py tests/unit/logic/ui_ux_ir/formalize/test_event_calculus.py tests/unit/logic/ui_ux_ir/formalize/test_tdfol.py tests/unit/logic/ui_ux_ir/formalize/test_dcec.py tests/unit/logic/ui_ux_ir/formalize/test_compiler.py -q
- Acceptance: Components/roles/bindings compile structurally; events/fluents/transitions compile behaviorally; temporal permissions/prohibitions/obligations compile without weakening; perception/knowledge/intention/consent/delegation compile cognitively; cross-view symbols and source references are exact.
- Gap task: Implement the next uncovered compiler leaf or integration mapping with a minimal grounded fixture.
- Refinement: One file and test owner per logic family; `compiler.py` is a later single-owner join.
- Embedding query: UI FOL frame logic F logic event calculus temporal deontic first order DCEC cognitive compiler source map
- AST query: UIFLogicCompiler UIEventCalculusCompiler UITDFOLCompiler UIDCECCompiler UIFormalizationCompiler

## UIR-G032 Decompilation equivalence and constrained synthesis

- Status: active
- Parent: UIR-G030
- Depends on: UIR-G031
- Fib priority: 5
- Track: synthesis
- Priority: P0
- Bundle: ui-ux-ir/roundtrip
- Parallel lane: uir-roundtrip
- Resource class: cpu-proof-solver
- Goal: Reconstruct supported UI semantics from typed formal views, verify layered round-trip equivalence, and synthesize bounded candidates from Intent/Invocation/IDL inputs plus reviewed formal constraints.
- Evidence: 941000000000000000032
- Evidence criteria: 941000000000000000032=golden and adversarial cases prove deterministic decompilation, ambiguity retention, source-grounding preservation, deontic non-weakening, bounded trace and graph equivalence, accessibility/modality parity, and candidate-only learned synthesis authority.
- Evidence source policy: Fresh reconstruction and round-trip receipts with exact inputs, policy, loss, and counterexamples qualify. Pixel/source equality and model self-evaluation do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/decompiler.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/roundtrip.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/synthesis.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/decompiler.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/roundtrip.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/synthesis.py
- Interfaces: UIFormalDecompiler@1, UISemanticRoundTrip@1, UISynthesizer@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/formalize/test_decompiler.py tests/unit/logic/ui_ux_ir/formalize/test_roundtrip.py tests/unit/logic/ui_ux_ir/formalize/test_synthesis.py -q
- Acceptance: Reconstruction fails or clarifies rather than inventing missing semantics; round trips evaluate graph, trace, formula, norm, accessibility, and modality equivalence; synthesis emits validated candidates and cannot claim proof or execution authority.
- Gap task: Add the smallest missing reconstruction, equivalence, clarification, or synthesis-admission rule and counterexample.
- Refinement: Implement decompiler and equivalence before learned candidate hooks; keep optional models lazy and injectable.
- Embedding query: formal logic to UI reconstruction semantic round trip equivalence synthesis ambiguity loss non weakening
- AST query: UIFormalDecompiler SemanticRoundTripPolicy UIEquivalenceResult UISynthesizer UISynthesisResult

## UIR-G040 MCP-IDL Intent IR TypeScript and ORB integration

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G020, UIR-G030
- Fib priority: 5
- Track: integration
- Priority: P0
- Bundle: ui-ux-ir/bridges
- Parallel lane: uir-bridge-integration
- Resource class: cpu-medium
- Goal: Bind UI/UX IR to existing MCP-IDL, Intent/Invocation IR, SwissKnife UI profiles, control-surface contracts, and ORB runtime without creating competing operation, procedure, policy, identity, or execution systems.
- Evidence: 941000000000000000040
- Evidence criteria: 941000000000000000040=fresh adapter and integration receipts prove exact stable references, Python/TypeScript codec compatibility, descriptor and program round trips, pre-invocation policy mediation, denial/confirmation non-execution, and end-to-end receipt correlation.
- Evidence source policy: Cross-language golden bytes plus focused adapter and broker/mediator tests qualify. Type checking, descriptor visibility changes, or an unmediated successful invocation do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters, swissknife/src/services/mcp/ui-ux-ir-codec.ts, swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, hallucinate_app/python/hallucinate_app/control_surface_mediator.py, swissknife/web/src/orb-dynamic-app-renderer.ts
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters, swissknife/src/services/mcp/ui-ux-ir-codec.ts, swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, hallucinate_app/python/hallucinate_app/control_surface_mediator.py, swissknife/web/src/orb-dynamic-app-renderer.ts
- Interfaces: MCPIDLUIIRAdapter@1, IntentUIIRAdapter@1, UIIRTypeScriptCodec@1, UIIRORBBridge@1, ControlSurfacePolicyParity@1, UIIRDynamicRendererSecurity@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/source_adapters -q; npm --prefix swissknife run test:run -- test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts; cd hallucinate_app && python -m pytest python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py -q
- Acceptance: UI action bindings retain exact verified IDL and Intent/Invocation identities and schemas; TypeScript and Python share the wire contract and fail-closed mediation outcomes; existing broker, router, mediator, and renderer consume UI/UX IR without moving authorization into presentation code, bypassing governed transport, accepting unsafe HTML, or duplicating formal semantics.
- Gap task: Implement the smallest missing source/codec/runtime bridge with an identity-bound fixture and bypass test.
- Refinement: Source adapters and new codec may run in parallel; existing broker/mediator edits belong to one later owner.
- Embedding query: MCP IDL ORB Intent IR invocation UI profile TypeScript codec control surface mediator integration
- AST query: InterfaceDescriptor IntentIRDocument InvocationIntentEnvelope UIIRTypeScriptCodec createDeonticORBEvaluator

## UIR-G041 Source adapters and cross-language codec

- Status: active
- Parent: UIR-G040
- Depends on: UIR-G020, UIR-G022
- Fib priority: 3
- Track: integration
- Priority: P0
- Bundle: ui-ux-ir/source-codecs
- Parallel lane: uir-source-codecs
- Resource class: cpu-medium
- Goal: Add bounded MCP-IDL and Intent/Invocation adapters and a SwissKnife TypeScript codec that preserve stable references, source maps, canonical collection semantics, validation diagnostics, and explicit import loss.
- Evidence: 941000000000000000041
- Evidence criteria: 941000000000000000041=adapter golden cases and Python/TypeScript vectors have identical canonical bytes/identity where required, reject unknown fields/versions/dangling references, and report all unsupported descriptor/program/UI-profile semantics.
- Evidence source policy: Fresh offline adapter and cross-language vector receipts qualify; source inspection and independently hashed but non-identical payloads do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl_identity.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/intent_ir.py, swissknife/src/services/mcp/ui-ux-ir-codec.ts
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl_identity.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/mcp_idl.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/intent_ir.py, swissknife/src/services/mcp/ui-ux-ir-codec.ts
- Interfaces: MCPIDLUIIRAdapter@1, IntentUIIRAdapter@1, UIIRTypeScriptCodec@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/source_adapters -q
- Acceptance: Adapters never execute imported content, infer grants, hide loss, or duplicate operation/procedure semantics; the TypeScript codec follows the canonical schema rather than defining a second one.
- Gap task: Add one missing adapter mapping or cross-language failure vector.
- Refinement: Python adapters and the new TypeScript codec use independent files; golden corpus ownership is deferred to assurance integration.
- Embedding query: UI IR MCP IDL adapter Intent invocation adapter TypeScript canonical codec source map loss
- AST query: MCPIDLUIIRAdapter IntentUIIRAdapter decodeUIIR canonicalizeUIIR

## UIR-G042 Runtime ORB and control-surface mediation

- Status: active
- Parent: UIR-G040
- Depends on: UIR-G031, UIR-G041, UIR-G051, UIR-G062
- Fib priority: 8
- Track: runtime
- Priority: P0
- Bundle: ui-ux-ir/orb
- Parallel lane: uir-orb
- Resource class: cpu-medium
- Goal: Make the existing deontic interface broker and control-surface mediator consume UI/UX IR bindings and runtime decisions while preserving one fail-closed governed invocation path.
- Evidence: 941000000000000000042
- Evidence criteria: 941000000000000000042=tests prove allowed invocations bind exact UI/action/IDL/policy/state identities, all blocking outcomes prevent transport execution, presentation state cannot bypass authorization, conflicts and duplicate modalities do not double invoke, and receipts correlate end to end.
- Evidence source policy: Focused broker/mediator tests with spy executors and exact receipts qualify. A UI snapshot or allow-only happy path does not.
- Outputs: swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts, hallucinate_app/python/hallucinate_app/control_surface_mediator.py, hallucinate_app/python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py, swissknife/web/src/orb-dynamic-app-renderer.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts
- Predicted files: swissknife/src/services/mcp/mcp-deontic-interface-broker.ts, swissknife/src/services/mcp/mcp-control-surface-mediator.ts, swissknife/src/services/mcp/mcp-orb-capability-router.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts, hallucinate_app/python/hallucinate_app/control_surface_mediator.py, hallucinate_app/python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py, swissknife/web/src/orb-dynamic-app-renderer.ts, swissknife/test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts
- Interfaces: UIIRORBBridge@1, ControlSurfaceMediation@1, ControlSurfacePolicyParity@1, UIIRDynamicRendererSecurity@1
- Validation: npm --prefix swissknife run test:run -- test/mcp-plus-plus/ui-ux-ir-orb-mediation.test.ts test/mcp-plus-plus/ui-ux-ir-dynamic-renderer-security.test.ts; cd hallucinate_app && python -m pytest python/hallucinate_app/test/test_ui_ux_ir_policy_parity.py -q
- Acceptance: UI shape and deontic visibility are advisory presentation results; TypeScript and Python policy paths re-evaluate every effect with the real bounded input and fail closed on missing/invalid policy; deny, confirm, defer, rate-limit, low-confidence, stale, and conflicting interactions do not reach the executor; rewrite/fallback is explicit and receipted; untrusted HTML and direct renderer transport cannot bypass the governed path.
- Gap task: Close one unmediated or incompletely receipted invocation path with a spy-executor regression test.
- Refinement: This is the sole task allowed to edit the existing broker and mediator for this program.
- Embedding query: UI IR deontic interface broker control surface mediator ORB authorization receipt duplicate input
- AST query: projectDeonticInterface createDeonticORBEvaluator mediateControlSurfaceInvocation UIMediationDecision

## UIR-G050 Capability-constrained target projection

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G020, UIR-G021, UIR-G022
- Fib priority: 5
- Track: projection
- Priority: P0
- Bundle: ui-ux-ir/projection
- Parallel lane: uir-projection-core
- Resource class: cpu-medium
- Goal: Negotiate target capabilities and solve bounded presentation constraints to produce deterministic projection artifacts and explicit degradation/loss receipts without weakening mandatory semantics.
- Evidence: 941000000000000000050
- Evidence criteria: 941000000000000000050=capability, solver, unsatisfiable, degradation, fallback, mandatory-affordance, accessibility, and deterministic-projection tests pass across reviewed desktop, mobile, glasses, and voice/headless profiles.
- Evidence source policy: Fresh projection fixtures and solver/loss receipts qualify. A renderer screenshot without semantic comparison does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection
- Interfaces: UIDeviceProfile@1, UIProjectionSolver@1, UIProjectionArtifact@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection -q
- Acceptance: Profiles describe capabilities rather than brands; projection is deterministic and bounded; mandatory actions, consent, error, consequence, confirmation, feedback, and accessibility alternatives are preserved or projection fails/falls back explicitly.
- Gap task: Implement the next uncovered capability predicate, constraint, loss category, or target projection fixture.
- Refinement: Core capability/solver/loss files land first; independent target adapters follow without editing the core.
- Embedding query: adaptive UI device capability negotiation constraint solver projection degradation loss desktop mobile glasses voice
- AST query: UIDeviceProfile CapabilityPredicate UIProjectionSolver UIProjectionArtifact ProjectionLoss

## UIR-G051 Web mobile glasses and voice/headless adapters

- Status: active
- Parent: UIR-G050
- Depends on: UIR-G041, UIR-G050
- Fib priority: 8
- Track: projection
- Priority: P1
- Bundle: ui-ux-ir/target-adapters
- Parallel lane: uir-target-adapters
- Resource class: cpu-large
- Goal: Implement reference adapters for DOM/ARIA web/desktop, mobile companion, Meta-glasses/spatial display, and voice/headless output against the shared projection artifact.
- Evidence: 941000000000000000051
- Evidence criteria: 941000000000000000051=each adapter passes semantic mapping, accessibility/modality, unsupported capability, fallback, deterministic rendering, and projection-loss tests; DOM import covers only its reviewed subset with source maps.
- Evidence source policy: Adapter unit tests plus browser/mobile/glasses/headless replay evidence qualify. Screenshots alone and platform-specific source type checks do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/dom_aria.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/web.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/mobile.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/glasses.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/voice.py, swissknife/src/services/mcp/ui-ux-ir-web-renderer.ts, swissknife/src/services/glasses/ui-ux-ir-glasses-adapter.ts, mobile/src/orb/uiUxIrMobileAdapter.js
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/dom_aria.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/web.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/mobile.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/glasses.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/voice.py, swissknife/src/services/mcp/ui-ux-ir-web-renderer.ts, swissknife/src/services/glasses/ui-ux-ir-glasses-adapter.ts, mobile/src/orb/uiUxIrMobileAdapter.js
- Interfaces: DOMARIAUIIRAdapter@1, UIIRWebRenderer@1, UIIRMobileAdapter@1, UIIRGlassesAdapter@1, UIIRVoiceProjection@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/projection/test_targets.py -q
- Acceptance: Target artifacts implement the same semantic actions/state/feedback; glasses respect action/text/update/field-of-view budgets and mobile fallback; voice/headless preserves prompts, choices, confirmations, results, and errors; unsupported source/render details are explicit.
- Gap task: Implement one target adapter or loss/fallback fixture without changing shared schema or projection core.
- Refinement: Web, mobile, glasses, and voice/headless use separate bundles/tasks and files despite sharing this goal.
- Embedding query: UI IR renderer DOM ARIA mobile Meta glasses spatial voice headless projection fallback
- AST query: DOMARIAAdapter renderUIIR UIIRMobileAdapter UIIRGlassesAdapter projectVoiceUI

## UIR-G060 Multimodal runtime and program orchestration

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G022, UIR-G040, UIR-G050
- Fib priority: 8
- Track: runtime
- Priority: P0
- Bundle: ui-ux-ir/runtime
- Parallel lane: uir-runtime-integration
- Resource class: cpu-medium
- Goal: Normalize multimodal input, resolve/fuse intentions, interpret state transitions, evaluate formal and runtime policy, invoke governed program bindings, emit feedback/fallback, and create deterministic replayable receipts.
- Evidence: 941000000000000000060
- Evidence criteria: 941000000000000000060=event, fusion, state-machine, policy, invocation-spy, fallback, feedback, stale/duplicate/conflict, replay, and receipt-integrity tests pass under bounded resources and exact declaration/projection/state/policy/program identities.
- Evidence source policy: Fresh deterministic runtime and adversarial receipts qualify. UI visibility, raw input recognition success, or an executor result without mediation lineage does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime
- Interfaces: UIInteractionEvent@1, UIMultimodalFusion@1, UIStateRuntime@1, UIMediationDecision@1, UIInteractionReceipt@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime -q
- Acceptance: All supported input surfaces share one canonical path; duplicate/conflicting signals cannot double execute; formal/runtime policy gates external effects; confirmation/fallback and program result mappings are explicit; traces replay deterministically without replaying effects.
- Gap task: Close the highest-risk event, fusion, transition, mediation, feedback, or receipt gap with a bounded executor-spy fixture.
- Refinement: Event adapters and fusion run independently; state/mediator integration waits for formal and ORB contracts; receipts land after decision shapes stabilize.
- Embedding query: multimodal UI runtime mouse touch speech gesture gaze neural band agent fusion state machine policy ORB receipts
- AST query: UIInteractionEvent UIMultimodalFusion UIStateRuntime UIMediator UIInteractionReceipt

## UIR-G061 Input normalization and multimodal fusion

- Status: active
- Parent: UIR-G060
- Depends on: UIR-G022
- Fib priority: 5
- Track: input
- Priority: P0
- Bundle: ui-ux-ir/input
- Parallel lane: uir-input
- Resource class: cpu-medium
- Goal: Define canonical interaction events and bounded adapters for pointer/keyboard/touch, speech, hand/gaze/head gesture, normalized Neural Band/captouch, and agent proposals, then fuse/correlate competing signals deterministically.
- Evidence: 941000000000000000061
- Evidence criteria: 941000000000000000061=fixtures cover confidence, calibration, freshness, consent/purpose, target resolution, redacted evidence refs, modality alternatives, simultaneous inputs, deduplication, cancellation, ambiguity, and high-risk clarification.
- Evidence source policy: Offline normalized-event and fusion receipts qualify. Raw device data, ASR text alone, or a simulator keypress without provenance and policy fields does not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/events.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/conventional.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/speech.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/embodied.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/fusion.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/events.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/conventional.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/speech.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/embodied.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/fusion.py
- Interfaces: UIInteractionEvent@1, UIInputAdapter@1, UIMultimodalFusion@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_events.py tests/unit/logic/ui_ux_ir/runtime/test_fusion.py -q
- Acceptance: Adapters expose semantic events rather than SDK objects or raw biometric/neural streams; low-confidence/high-impact input clarifies; correlated inputs select one intent; live human priority over agent proposals does not bypass policy.
- Gap task: Add one missing input normalization or fusion/conflict case with privacy-safe fixtures.
- Refinement: Conventional, speech, gesture/gaze, Neural Band/captouch, and fusion work use exclusive test files and may run in parallel after the event envelope lands.
- Embedding query: normalized multimodal input mouse keyboard touch microphone speech hand gaze head neural band captouch agent fusion
- AST query: UIInteractionEvent UIInputAdapter SpeechInputAdapter GestureInputAdapter NeuralBandIntentAdapter fuse_interactions

## UIR-G062 State policy invocation feedback and receipts

- Status: active
- Parent: UIR-G060
- Depends on: UIR-G030, UIR-G041, UIR-G050, UIR-G061
- Fib priority: 8
- Track: runtime
- Priority: P0
- Bundle: ui-ux-ir/mediation
- Parallel lane: uir-mediation
- Resource class: cpu-proof-solver
- Goal: Implement the bounded state interpreter and policy mediator that maps normalized events to candidate transitions, governed invocations, results, feedback/fallback, immutable receipts, and side-effect-free replay.
- Evidence: 941000000000000000062
- Evidence criteria: 941000000000000000062=state/property and executor-spy tests cover all decision outcomes, guards, temporal/deontic/cognitive checks, confirmation, rewrite/fallback, rollback/compensation, result mapping, stale state, exact receipt bindings, tampering, and replay without effects.
- Evidence source policy: Fresh runtime tests and typed policy/monitor/proof evidence appropriate to each claim qualify. A passing state trace cannot claim theorem proof and an allow decision cannot prove accessibility or effect success.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/state_machine.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/mediator.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/receipts.py
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/state_machine.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/mediator.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/receipts.py
- Interfaces: UIStateRuntime@1, UIMediator@1, UIInteractionReceipt@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/runtime/test_state_machine.py tests/unit/logic/ui_ux_ir/runtime/test_mediator.py tests/unit/logic/ui_ux_ir/runtime/test_receipts.py -q
- Acceptance: Only an explicit allowed decision can create an invocation request; every other outcome remains non-executing; state/effect/feedback ordering is deterministic; rollback and verification are explicit; replay validates decisions and transitions without repeating side effects.
- Gap task: Close one missing decision, transition, invocation, fallback, or receipt-integrity path with an executor spy.
- Refinement: State interpreter lands before mediator; receipts stabilize after decision and invocation envelopes.
- Embedding query: UI state runtime temporal deontic policy mediator governed invocation confirmation fallback feedback receipt replay
- AST query: UIStateRuntime UIMediationDecision UIInvocationRequest UIInteractionReceipt replay_interactions

## UIR-G070 Accessibility privacy security and conformance assurance

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G030, UIR-G050, UIR-G060
- Fib priority: 13
- Track: assurance
- Priority: P0
- Bundle: ui-ux-ir/assurance
- Parallel lane: uir-assurance
- Resource class: cpu-medium
- Goal: Prove or explicitly measure accessibility/localization and modality equivalence, sensor/privacy/consent controls, expression/import security, authorization non-bypass, schema/round-trip properties, and Python/TypeScript golden parity.
- Evidence: 941000000000000000070
- Evidence criteria: 941000000000000000070=fresh accessibility, privacy, threat-model, property/fuzz/model, semantic-mutation, and cross-language conformance receipts report no unresolved critical violation and preserve typed authority and explicit unknown states.
- Evidence source policy: Deterministic validators, property/model tests, adversarial fixtures, and exact canonical vectors qualify. Checklists, screenshots, type checks, model reviews, and best-effort warnings alone do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/accessibility.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/privacy.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/security.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/conformance.py, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_conformance.py, swissknife/test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/accessibility.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/privacy.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/security.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/conformance.py, external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1, external/ipfs_datasets/tests/unit/logic/ui_ux_ir/test_conformance.py, swissknife/test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts
- Interfaces: UIIRConformance@1, UIIRPrivacyPolicy@1, UIIRCrossLanguageParity@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_conformance.py -q
- Acceptance: Essential actions/outputs have alternatives; focus/name/role/state/feedback/localization rules hold; raw sensitive input is minimized and consent/purpose bound; imports and expressions cannot execute code; authorization bypasses fail; canonical and semantic parity holds across languages.
- Gap task: Add the smallest missing adversarial, property, accessibility, privacy, or parity case and its deterministic gate.
- Refinement: Accessibility/privacy validators, property/model testing, and golden parity use independent files; cross-language closeout follows stable codecs.
- Embedding query: UI IR accessibility localization privacy consent biometric neural input security property testing conformance parity
- AST query: UIIRConformanceReport AccessibilityValidator PrivacyPolicy SemanticRoundTripProperty CrossLanguageVector

## UIR-G080 Public integration and vertical pilots

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G040, UIR-G050, UIR-G060, UIR-G070
- Fib priority: 21
- Track: integration
- Priority: P1
- Bundle: ui-ux-ir/pilots
- Parallel lane: uir-public-integration
- Resource class: cpu-large
- Goal: Register the stable package/API/bridge surface once and demonstrate the complete architecture through representative web/mobile, destructive-policy, Meta-glasses, and dynamic program-interface pilots.
- Evidence: 941000000000000000080
- Evidence criteria: 941000000000000000080=cold import and registry tests plus four end-to-end pilot receipts bind canonical declaration, formal views, target projection/loss, inputs, policy, state, invocation, feedback, and result without private deep imports or unmediated effects.
- Evidence source policy: Fresh public API, registry, and pilot E2E receipts qualify. Internal module imports, mocked allow-only calls, or UI screenshots without receipt chains do not.
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/api.py, external/ipfs_datasets/ipfs_datasets_py/logic/submodule_registry.py, external/ipfs_datasets/ipfs_datasets_py/logic/bridge/registry.py, external/ipfs_datasets/tests/integration/logic/ui_ux_ir
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/model/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/formalize/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/source_adapters/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/runtime/input/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/assurance/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/api.py, external/ipfs_datasets/ipfs_datasets_py/logic/submodule_registry.py, external/ipfs_datasets/ipfs_datasets_py/logic/bridge/registry.py, external/ipfs_datasets/tests/integration/logic/ui_ux_ir
- Interfaces: UIUXIRPublicAPI@1, UIUXIRBridgeRegistration@1, UIUXIRPilots@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_internal_api.py tests/unit/logic/ui_ux_ir/test_public_api.py tests/integration/logic/ui_ux_ir -q
- Acceptance: Public imports are lazy and reviewed; schema and bridge registration is deterministic; all four pilots exercise actual contracts and failure paths; no pilot relies on raw EMG, visual hiding as authorization, or target-specific semantics in the canonical schema.
- Gap task: Land the next missing public integration or pilot path after its dependencies pass.
- Refinement: One task owns internal subpackage exports and a serialized successor owns root/public exports and registries; each pilot has exclusive fixtures and may run independently afterward.
- Embedding query: UI UX IR public API registry vertical pilot responsive form destructive confirmation Meta glasses agent supervisor program
- AST query: UIUXIR_PUBLIC_API LogicSubmoduleSpec LogicBridgeSpec responsive_form_pilot destructive_workflow_pilot meta_glasses_pilot supervisor_program_pilot

## UIR-G081 Cross-target form destructive flow glasses and program pilots

- Status: active
- Parent: UIR-G080
- Depends on: UIR-G051, UIR-G062, UIR-G070
- Fib priority: 21
- Track: pilots
- Priority: P1
- Bundle: ui-ux-ir/pilot-suite
- Parallel lane: uir-pilots
- Resource class: cpu-large
- Goal: Exercise four reference verticals: responsive schema form on web/mobile, destructive workflow with confirmation/rollback, Meta-glasses constrained UI with normalized D-pad/Neural Band/captouch and mobile fallback, and a dynamic agent-supervisor/program UI synthesized from MCP-IDL plus Intent IR.
- Evidence: 941000000000000000081
- Evidence criteria: 941000000000000000081=each pilot has canonical and formal artifacts, target projections and loss receipts, positive and negative interaction traces, accessibility/privacy results, governed invocation receipts, deterministic replay, and asserted user-visible feedback/recovery.
- Evidence source policy: Hardware-free E2E receipts using the production contract surfaces qualify; screenshots, isolated render snapshots, and direct executor calls do not.
- Outputs: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots, external/ipfs_datasets/tests/integration/logic/ui_ux_ir
- Predicted files: external/ipfs_datasets/tests/fixtures/ui_ux_ir/pilots, external/ipfs_datasets/tests/integration/logic/ui_ux_ir
- Interfaces: UIUXIRPilotSuite@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/integration/logic/ui_ux_ir -q
- Acceptance: The same semantic actions survive cross-target projection; destructive calls cannot execute before confirmation; glasses use supported normalized inputs and fall back safely; the program UI reflects IDL/Intent state without granting agent authority.
- Gap task: Implement one missing pilot fixture, negative path, receipt assertion, or cross-target equivalence check.
- Refinement: Each pilot is a separate task and file owner; shared integration fixtures land first.
- Embedding query: UI IR pilot responsive web mobile destructive confirmation rollback Meta glasses neural captouch program supervisor dynamic interface
- AST query: responsive_form_pilot destructive_workflow_pilot meta_glasses_pilot supervisor_program_pilot

## UIR-G090 Performance E2E evidence documentation and release closure

- Status: active
- Parent: UIR-G000
- Depends on: UIR-G070, UIR-G080, UIR-G081
- Fib priority: 34
- Track: release
- Priority: P1
- Bundle: ui-ux-ir/release
- Parallel lane: uir-release
- Resource class: cpu-medium
- Goal: Bound complexity and latency, run hardware-free browser/mobile/glasses replay, publish API/extension/migration guidance, and close the program only from a current-tree conformance receipt.
- Evidence: 941000000000000000090
- Evidence criteria: 941000000000000000090=benchmark and size/timeout bounds pass, E2E simulator evidence covers every target and high-risk outcome, documentation matches public APIs and hardware assumptions, and the root conformance test aggregates all mandatory current-tree evidence with no unresolved critical gap.
- Evidence source policy: Fresh benchmark, simulator, documentation-link/API, and root conformance receipts bound to exact trees qualify. Historical reports, stale screenshots, drained tasks, and passing narrow unit selections do not.
- Outputs: external/ipfs_datasets/tests/benchmarks/test_ui_ux_ir_performance.py, swissknife/test/e2e/ui-ux-ir-pilots.spec.ts, swissknife/build-tools/configs/playwright.ui-ux-ir.config.ts, mobile/src/orb/__tests__/uiUxIrPilotReplay.test.js, external/ipfs_datasets/docs/logic/UI_UX_IR_GUIDE.md, external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py
- Predicted files: external/ipfs_datasets/tests/benchmarks/test_ui_ux_ir_performance.py, swissknife/test/e2e/ui-ux-ir-pilots.spec.ts, swissknife/build-tools/configs/playwright.ui-ux-ir.config.ts, mobile/src/orb/__tests__/uiUxIrPilotReplay.test.js, external/ipfs_datasets/docs/logic/UI_UX_IR_GUIDE.md, external/ipfs_datasets/tests/integration/logic/test_ui_ux_ir_conformance.py
- Interfaces: UIUXIRReleaseGate@1
- Validation: cd external/ipfs_datasets && python -m pytest tests/benchmarks/test_ui_ux_ir_performance.py tests/integration/logic/test_ui_ux_ir_conformance.py -q
- Acceptance: Measured limits replace provisional budgets where justified; every optional dependency and external call is bounded; hardware-free E2E exercises fallback and failure; guide documents extension and semantic-loss rules; root receipt enumerates every child and selected validation population.
- Gap task: Close the next measured performance, E2E, documentation, or evidence-aggregation gap without weakening a gate.
- Refinement: Benchmark, E2E, and documentation tasks can run independently; the conformance aggregator is the final single-owner task.
- Embedding query: UI UX IR benchmark latency size bounded E2E simulator documentation migration extension release conformance
- AST query: UIUXIRBenchmark UIUXIRE2E UIUXIRReleaseReceipt test_ui_ux_ir_conformance
