# VerifiedGuiOptimizer Supervisor Taskboard (VGO)

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix
`## VGO-` and board namespace `verified-gui-optimizer-v1`. The selected
end-to-end target is the SwissKnife **Agent Supervisor** screen implemented by
`swissknife/web/js/apps/agent-supervisor.js`. Architecture must remain reusable
for other screens, but no task may expand into optimizing every application.

## Normative execution doctrine

- Evidence, not aesthetic preference, controls automatic acceptance. Formal
  checks cover only declared bounded state, interaction, form, modal, identity,
  action-binding, and policy invariants. Visual quality stays heuristic or
  human-reviewed and is never described as proved optimal.
- Analysis classification (`exact`, `conservative`, `heuristic`, `opaque`) is
  independent from verification status (`verified`, `structurally_valid`,
  `integrity_valid`, `unverified`, `stale`, `invalid`, `simulated`). A content
  identity alone never upgrades an evidence claim.
- Implement standalone GUI contracts. Do not import or depend on a prior
  semantic-index, semantic-capsule, proof-cache, or model-routing package. The
  required `UiSemanticCapsule` is a new, closed GUI-specific record built from
  source evidence. The provider-neutral proposal interface is not a router.
- Static analysis may parse source but must never evaluate or import arbitrary
  repository code. Opaque or stale components force bounded raw-source context.
- Use canonical SHA-256/CIDv1 facilities already committed in
  `ipfs_datasets_py` or `ipfs_accelerate_py`; never manufacture CID-looking
  labels. Closed schemas reject unknown fields.
- Browser fixtures use controlled data only: no production credentials,
  services, MCP tools, user data, remote scripts, arbitrary filesystem paths,
  or arbitrary subprocess commands.
- UI visibility and enabled state are not authorization. The host re-evaluates
  action, arguments, policy freshness, and confirmation. Browser policy output
  is never authoritative, and confirmation remains bound to the exact action
  and arguments.
- Every proposal declares files, components, state and visual effects, tests,
  screenshots, and acceptance criteria. Undeclared or excessive edits, deleted
  tests, arbitrary HTML execution, weakened checks, unrelated applications,
  credential/backend-authority changes, or unverified action-binding changes
  are rejected or sent to human review.
- Four strict task-ID hash shards use isolated worktrees and the serial merge queue.
  Tasks own only declared files, keep receipts content-addressed, and leave a
  rejected patch outside the canonical branch.
- Wave admission is topological: explicit `Depends on` edges are authoritative,
  and tasks in the same wave never acquire an implicit dependency on one
  another.
- Pending implementation tasks fail closed on an empty candidate. No-change
  completion is forbidden unless the exact task revision explicitly declares
  `No-change completion: allowed` and the supervisor issues its separate,
  attempt-bound no-change policy receipt; a green inherited test suite alone
  is never completion authority.
- Every validation command starts at the superproject root and inherits the
  sealed supervisor runtime, including Node 22/npm 10 on `PATH` and the three
  repository import roots on `PYTHONPATH`. Tasks must not install dependencies
  into their isolated worktrees or fall back to the host Node runtime. Browser,
  benchmark, build, and other long validations stream line-oriented progress or
  emit a journal heartbeat comfortably inside the configured stall window.
- Evidence bytes such as screenshots, traces, and accessibility payloads live
  in the host-owned content-addressed artifact store from VGO-054. Durable
  manifests and receipts under `implementation_plan/evidence/verified_gui_optimizer/`
  bind and rehash those artifacts; ephemeral supervisor state alone is never
  completion evidence.
- A task that owns submodule files commits each nested repository first, stages
  only the resulting exact gitlinks, and hands off one atomic superproject
  candidate. A task spanning multiple submodules must validate every affected
  runtime and leave every nested worktree clean before that handoff; partial
  gitlink promotion is forbidden.

## Execution waves

- Wave 0: `VGO-000` (lane 3).
- Wave 1: `VGO-001` (lane 1), `VGO-009` (lane 3).
- Wave 2: `VGO-002` (lane 0).
- Wave 3: `VGO-003` (lane 2), `VGO-010` (lane 3), `VGO-011` (lane 0).
- Wave 4: `VGO-012` (lane 2), `VGO-016` (lane 1).
- Wave 5: `VGO-020` (lane 1), `VGO-021` (lane 3), `VGO-023` (lane 2),
  `VGO-027` (lane 0).
- Wave 6: `VGO-030` (lane 3), `VGO-031` (lane 1), `VGO-032` (lane 0),
  `VGO-034` (lane 2).
- Wave 7: `VGO-040` (lane 0), `VGO-043` (lane 2), `VGO-045` (lane 3).
- Wave 8: `VGO-041` (lane 1), `VGO-050` (lane 1), `VGO-051` (lane 0),
  `VGO-061` (lane 3).
- Wave 9: `VGO-054` (lane 3), `VGO-062` (lane 2).
- Wave 10: `VGO-053` (lane 2).
- Wave 11: `VGO-060` (lane 0), `VGO-070` (lane 1), `VGO-071` (lane 2),
  `VGO-075` (lane 3).
- Wave 12: `VGO-068` (lane 1).
- Wave 13: `VGO-072` (lane 0).
- Wave 14: `VGO-083` (lane 1), `VGO-086` (lane 0).
- Wave 15: `VGO-080` (lane 2).
- Wave 16: `VGO-081` (lane 3).
- Wave 17: `VGO-090` (lane 3), `VGO-096` (lane 1).
- Wave 18: `VGO-091` (lane 2).
- Wave 19: `VGO-093` (lane 0).
- Wave 20: `VGO-099` (lane 0).

## VGO-000 Seal the supervisor-native control plane

- Status: completed
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: control-plane
- Depends on:
- Goal id: VGO-G010
- Outputs: implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md, implementation_plan/docs/49-verified-gui-optimizer.objectives.md, implementation_plan/docs/49-verified-gui-optimizer.todo.md, config/verified_gui_optimizer_scheduler.json, scripts/validate_verified_gui_optimizer_board.py, scripts/ops/agent_supervisor/implementation_supervisor_entry.py, scripts/ops/verified_gui_optimizer_vgo001_oracle.py, scripts/ops/verified_gui_optimizer_vgo009_oracle.py, scripts/ops/verified_gui_optimizer_status.py
- Validation: python3 scripts/validate_verified_gui_optimizer_board.py --check-all
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/control-seal
- Parallel lane: vgo-lane-3
- Resource class: cpu-small
- Resource stage: planning
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md, implementation_plan/docs/49-verified-gui-optimizer.objectives.md, implementation_plan/docs/49-verified-gui-optimizer.todo.md, config/verified_gui_optimizer_scheduler.json, scripts/validate_verified_gui_optimizer_board.py, scripts/ops/agent_supervisor/implementation_supervisor_entry.py, scripts/ops/verified_gui_optimizer_vgo001_oracle.py, scripts/ops/verified_gui_optimizer_vgo009_oracle.py, scripts/ops/verified_gui_optimizer_status.py
- Interfaces: ConfiguredBoardScheduler@1, MarkdownTaskSource@1, VgoGoalHeap@1
- Conflict policy: Operator-owned protected controls; managed agents must not edit them.
- Preconditions: Exact reviewed superproject revision and clean exact SwissKnife, datasets, and accelerator gitlinks are recorded.
- Effects: Seals scope, shards, authority doctrine, selected target, source bindings, retry bounds, and monitoring paths before implementation starts.
- Evidence subset: Board-validator JSON, Git revision record, baseline command record, configured-scheduler preflight
- Acceptance: Validator and scheduler preflight pass; all 42 IDs occur exactly once; protected controls are tracked; after the audited repair projection the only ready implementation claims are VGO-001 and VGO-009, while VGO-002 is dependency-blocked on the authoritative Python wire contract and VGO-003 remains dependency-blocked until VGO-002 completes.

## VGO-001 Define closed GUI optimizer data models

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: data-contracts
- Depends on: VGO-000
- Goal id: VGO-G020
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/models.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/schema.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_models.py
- Validation: PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ops/verified_gui_optimizer_vgo001_oracle.py --check-all && cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_models.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/models
- Parallel lane: vgo-lane-1
- Resource class: cpu-small
- Resource stage: contracts
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/__init__.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/models.py, external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/schema.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_models.py
- Interfaces: GuiApplicationIdentity@1, GuiScreenIdentity@1, UiComponentIdentity@1, UiComponentVersion@1, UiDependencyEdge@1, UiStateDefinition@1, UiEventDefinition@1, UiTransitionDefinition@1, UiActionBinding@1, UiLayoutConstraint@1, UiAccessibilityContract@1, UiSemanticCapsule@1, UiChangeSet@1, UiInvalidationPlan@1, UiEvaluationScenario@1, UiBaseline@1, UiContextPack@1, GuiImprovementProposal@1, VisualRegressionReceipt@1, AccessibilityReceipt@1, InteractionReceipt@1, UiConstraintReceipt@1, GuiImprovementReceipt@1
- Conflict policy: Own only the new standalone datasets GUI contract package; preserve existing IR and verification packages.
- Preconditions: VGO schema/version doctrine is sealed and canonical JSON facilities are available; earlier candidates coerced wrong JSON container types through tuple conversion, admitted explicit null for array fields, erased or failed to detect canonical Unicode mapping-key collisions, combined required semantic fields, omitted exact context payloads and computed token accounting, admitted contradictory receipts, and created undeclared probe artifacts that must not remain in the repository; the latest frozen candidate also stripped significant whitespace from exact source content, carried only capsule IDs rather than unchanged capsule payloads, retained mutable non-NFC or non-JSON nested values, coerced Python objects at wire boundaries, rejected truthful negative compression, allowed epsilon region overflow, and synthesized missing nested schema identities.
- Effects: Defines versioned finite wire records for every required identity, graph, state, evaluation, proposal, and receipt boundary.
- Evidence subset: Required-model inventory, closed-schema rejection vectors, enum and finite-bound tests, uniquely named machine-counted ARRAY_WIRE_CASES covering every declared JSON-array field including every newly introduced field and at least the 68 fields currently enumerated across all 23 required sample models, omission-versus-explicit-null and every wrong-container vector, a NULL_ARRAY_REGRESSIONS manifest equal to the literal sorted qualified-field set {AccessibilityReceipt@1.manual_check_ids, AccessibilityReceipt@1.unsupported_criteria, AccessibilityReceipt@1.violation_ids, GuiImprovementProposal@1.expected_screenshot_ids, GuiImprovementProposal@1.expected_test_ids, GuiImprovementProposal@1.state_effect_ids, GuiImprovementReceipt@1.rejection_reasons, InteractionReceipt@1.action_invocation_ids, InteractionReceipt@1.event_ids, InteractionReceipt@1.focus_sequence, InteractionReceipt@1.recovery_ids, InteractionReceipt@1.unresolved_observation_ids, UiAccessibilityContract@1.required_names, UiAccessibilityContract@1.required_roles, UiBaseline@1.artifact_digests, UiChangeSet@1.action_ids, UiChangeSet@1.component_ids, UiChangeSet@1.state_ids, UiConstraintReceipt@1.unsupported_check_ids, UiConstraintReceipt@1.violated_check_ids, UiContextPack@1.acceptance_criteria, UiContextPack@1.affected_test_ids, UiContextPack@1.artifact_digests, UiContextPack@1.capsule_ids, UiContextPack@1.escalation_conditions, UiContextPack@1.invariant_failure_ids, UiContextPack@1.state_machine_ids, UiContextPack@1.style_token_paths, UiEvaluationScenario@1.tags, UiInvalidationPlan@1.affected_check_ids, UiInvalidationPlan@1.affected_component_ids, UiInvalidationPlan@1.affected_scenario_ids, UiSemanticCapsule@1.action_binding_ids, UiSemanticCapsule@1.action_side_effects, UiSemanticCapsule@1.child_component_ids, UiSemanticCapsule@1.dependency_edge_ids, UiSemanticCapsule@1.emitted_event_ids, UiSemanticCapsule@1.keyboard_focus_behavior, UiSemanticCapsule@1.known_violation_ids, UiSemanticCapsule@1.layout_responsive_behavior, UiSemanticCapsule@1.localization_keys, UiSemanticCapsule@1.prop_names, UiSemanticCapsule@1.screenshot_ids, UiSemanticCapsule@1.state_variable_ids, UiSemanticCapsule@1.test_ids, UiSemanticCapsule@1.transition_ids, UiSemanticCapsule@1.unresolved_dynamic_behavior, UiSemanticCapsule@1.visible_state_ids, UiTransitionDefinition@1.effect_ids, VisualRegressionReceipt@1.component_version_ids, VisualRegressionReceipt@1.expected_change_regions, VisualRegressionReceipt@1.forbidden_change_regions}, a complete post-repair scalar string/digest field inventory including every newly introduced field, a NULL_SCALAR_REGRESSIONS manifest equal to the literal sorted qualified-field set {GuiApplicationIdentity@1.display_name, GuiApplicationIdentity@1.repository_root, GuiImprovementProposal@1.context_pack_id, GuiImprovementProposal@1.visual_effect_summary, GuiImprovementReceipt@1.context_pack_id, GuiImprovementReceipt@1.invalidation_plan_id, GuiImprovementReceipt@1.patch_digest, GuiScreenIdentity@1.route_id, InteractionReceipt@1.confirmation_id, UiAccessibilityContract@1.component_id, UiAccessibilityContract@1.notes, UiActionBinding@1.component_id, UiActionBinding@1.policy_id, UiChangeSet@1.summary, UiComponentIdentity@1.screen_id, UiComponentVersion@1.localization_digest, UiConstraintReceipt@1.solver_id, UiContextPack@1.baseline_id, UiContextPack@1.excluded_context_explanation, UiDependencyEdge@1.notes, UiEventDefinition@1.description, UiInvalidationPlan@1.fallback_explanation, UiLayoutConstraint@1.breakpoint, UiLayoutConstraint@1.component_id, UiSemanticCapsule@1.accessibility_contract_id, UiSemanticCapsule@1.empty_behavior, UiSemanticCapsule@1.error_behavior, UiSemanticCapsule@1.loading_behavior, UiSemanticCapsule@1.source_revision, UiSemanticCapsule@1.success_behavior, UiStateDefinition@1.description, UiStateDefinition@1.label, UiTransitionDefinition@1.guard, VisualRegressionReceipt@1.browser, VisualRegressionReceipt@1.browser_version}, required schema/interface vectors, registered optimizer-schema vectors, non-string and NFC-equivalent canonical mapping-key collision vectors, accepted/rejected/visual/constraint cross-field receipt-consistency vectors, exact round-trip type preservation, distinct capsule layout/responsive/keyboard/focus fields, exact context source/style/test/state/violation/route/action/screenshot payload inventory, exact token-accounting equations, closed structured visual-region records, browser identity vectors, undeclared-artifact absence, exact raw-content preservation vectors covering leading/trailing spaces, tabs, blank lines, final LF, and CRLF, unchanged parent/child capsule payload vectors rather than ID-only vectors, recursive JSON-shape/NFC/deep-copy immutability vectors, strict wire-decoder vectors rejecting Python Enum and nested model instances, negative-compression plus malformed/mismatched compression input vectors, exact no-epsilon region-bound vectors, nested interface/schema omission vectors
- Acceptance: Every required model is versioned, deterministically serializable, and requires its exact schema and interface identity on wire input; decoders reject unknown fields, invalid enum values, unregistered optimizer schema versions, non-finite values, non-string mapping keys, non-NFC keys, exact or NFC-equivalent canonical-key collisions, explicit null for every nonnullable field, and wrong JSON container types before any tuple, list, mapping, string, numeric, or boolean coercion; the suite exposes uniquely named machine-counted case manifests, rejects duplicate case IDs, inventories and tests every post-repair JSON-array field including every newly introduced field and at least the 68 currently enumerated fields across the 23 required sample models, and proves every array-valued wire field accepts only a JSON list while rejecting Python tuples, explicit null, mappings, strings, numeric values, and booleans; NULL_ARRAY_REGRESSIONS must equal the literal 52-entry qualified-field set in Evidence subset with no omissions or substitutions, and removed legacy combined fields remain literal unknown-field rejection regressions; the suite also inventories every post-repair scalar string and digest field including newly introduced fields; NULL_SCALAR_REGRESSIONS must equal the literal 35-entry qualified-field set in Evidence subset with no omissions or substitutions, so present null never becomes an empty string; arrays never decode as mappings, omitted optional fields are distinguished from present null, the explicitly nullable source_span mapping remains nullable, and round trips preserve exact wire types; an automatically accepted GuiImprovementReceipt requires nonempty invalidation_plan_id, context_pack_id, patch_digest, and all four nonempty visual_receipt_ids, accessibility_receipt_ids, interaction_receipt_ids, and constraint_receipt_ids lists, plus verification_status in the exact set {verified, integrity_valid}; it cannot carry rejection reasons and therefore rejects structurally_valid, unverified, stale, invalid, or simulated evidence as automatic-acceptance authority, while rejected values require reasons; UiConstraintReceipt statuses, violated_check_ids, and unsupported_check_ids agree exactly and reject unknown or simultaneously satisfied-and-unsupported checks; VisualRegressionReceipt rejects PASS with human review required, REVIEW without human review, or empty browser/version, and represents every expected or forbidden change region as a closed record containing a unique stable region_id, finite normalized x, y, width, and height coordinates with x >= 0, y >= 0, width > 0, height > 0, x + width <= 1, and y + height <= 1, plus a nonempty evidence reason; expected and forbidden region IDs are disjoint; UiSemanticCapsule has distinct fields for action side effects, layout role, responsive behavior, keyboard interactions, and focus behavior rather than combined prose substitutes; UiContextPack carries exact editable raw-source content, exact relevant CSS or design-token content, exact affected test paths and content, unchanged parent/child capsules, the current state-machine payload, formal failures, accessibility violations, visual references, screenshot descriptions and artifact IDs, affected routes and action bindings, metric baseline, acceptance criteria, exclusions, and escalation conditions rather than only paths or IDs; its accounting records safe nonnegative integer raw_source_tokens, capsule_tokens, screenshot_analysis_tokens, other_context_tokens, source_tokens_replaced_by_capsules, ordinary_raw_dependency_tokens, and total_estimated_prompt_tokens plus a safe positive integer token_budget; total_estimated_prompt_tokens equals raw_source_tokens plus capsule_tokens plus screenshot_analysis_tokens plus other_context_tokens; ordinary_raw_dependency_tokens equals raw_source_tokens plus source_tokens_replaced_by_capsules plus screenshot_analysis_tokens plus other_context_tokens; source_tokens_replaced_by_capsules is never counted as prompt usage; compression_ratio is derived exactly as (ordinary_raw_dependency_tokens - total_estimated_prompt_tokens) / ordinary_raw_dependency_tokens rather than trusted from input; ordinary_raw_dependency_tokens is positive and total_estimated_prompt_tokens cannot exceed token_budget; VisualRegressionReceipt also carries structural metrics, unexplained-difference and manual-review thresholds; the Python schema registry is the authoritative wire vocabulary that the dependent TypeScript contract must mirror; analysis class remains separate from verification status; no undeclared artifact or dependency on excluded prior subsystems remains; the declared suite contains literal regressions for every earlier false-green case; exact raw-source, CSS/design-token, and affected-test content strings preserve every code point including leading/trailing whitespace, tabs, blank lines, final LF, and CRLF without trimming or normalization; unchanged parent and child capsules are retained as full closed capsule payloads, not only IDs; every nested context mapping and array is recursively validated as a closed JSON value with exact built-in wire types, finite numbers, string NFC keys, defensive deep-copy or equivalent immutability, and stable to_dict output after mutation of caller-owned inputs; from_dict rejects Python Enum, dataclass, model, mapping-proxy, tuple, and other constructor-only instances instead of converting them, while every versioned nested wire record requires its explicit exact interface and schema_version rather than synthesizing defaults; an equation-consistent negative compression_ratio is represented truthfully, any supplied compression_ratio must be an exact finite number equal to the derived equation and malformed, non-finite, or mismatched values reject, while omission may derive it; normalized region containment uses exact x + width <= 1 and y + height <= 1 comparisons with no positive epsilon; the declared suite contains named literal regressions for these seven frozen-candidate failures and every earlier false-green case.

## VGO-002 Implement the non-executing GUI static scanner core

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: static-analysis
- Depends on: VGO-001
- Goal id: VGO-G030
- Outputs: swissknife/src/services/gui-optimizer/models.ts, swissknife/src/services/gui-optimizer/scanner.ts, swissknife/test/unit/services/gui-optimizer/scanner.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/scanner.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/scanner-core
- Parallel lane: vgo-lane-0
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/models.ts, swissknife/src/services/gui-optimizer/scanner.ts, swissknife/test/unit/services/gui-optimizer/scanner.test.ts
- Interfaces: GuiStaticScanner@1, GuiSourceFinding@1, GuiExtractionConfidence@1
- Conflict policy: Use the TypeScript compiler API for JS/TS/JSX/TSX and bounded non-executing parser/tokenizer adapters for standalone HTML/CSS; never evaluate modules, templates, browser globals, plugins, or repository scripts.
- Preconditions: The live Agent Supervisor source, manifest, route registration, and test surfaces are identified; VGO-001 has sealed the authoritative Python wire schema; the first candidate is known to diverge from that schema and to misclassify computed actions, delegated events, dynamic imports and components, and unknown widgets as exact, and to emit colliding anonymous-element identities plus unresolved graph targets.
- Effects: Defines strict TypeScript decoders aligned with the Python wire models and extracts bounded React, TSX, JSX, standalone HTML/CSS, templates, props, state, events, accessibility, style, responsive, localization, action, and host-boundary facts with spans and confidence.
- Evidence subset: Parser fixtures for JSX and template strings, negative execution canary, extractor-version fixtures, Python/TypeScript wire-schema vocabulary and key conformance, computed-action and delegated-event vectors, dynamic-import/component and unknown-widget vectors, prop/focus/keyboard/policy/action-binding extraction, parent/render linkage, duplicate-anonymous-element identity, emitted-edge target resolution, malformed-source and invalid-option vectors
- Acceptance: TypeScript schema versions, component kinds, extraction methods, source spans, edge fields, and all shared wire keys and enums mirror the authoritative VGO-001 Python registry; supported facts are deterministic; dynamic HTML, imperative DOM, uncontrolled event delegation, dynamically loaded styles, remote or unknown widgets, dynamically generated components, computed actions, unresolved globals, and runtime-generated forms downgrade classification and record the unresolved cause; props plus focus, keyboard, policy, action, parent, child, contains, and renders facts are emitted when statically present; stable logical identities do not collide for distinct anonymous elements and do not use line numbers as their primary identity; every emitted edge target resolves to an emitted stable identity or is explicitly unresolved; malformed source and invalid language or non-finite option values cannot be labeled exact; no arbitrary source code executes.

## VGO-003 Define the deterministic evaluation scenario catalog

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: scenario-contracts
- Depends on: VGO-002
- Goal id: VGO-G060
- Outputs: swissknife/src/services/gui-optimizer/scenario-catalog.ts, swissknife/test/fixtures/gui-optimizer/scenarios/agent-supervisor-scenarios.json, swissknife/test/unit/services/gui-optimizer/scenario-catalog.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/scenario-catalog.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/scenario-catalog
- Parallel lane: vgo-lane-2
- Resource class: cpu-small
- Resource stage: evaluation
- Implementation timeout seconds: 5400
- Predicted files: swissknife/src/services/gui-optimizer/scenario-catalog.ts, swissknife/test/fixtures/gui-optimizer/scenarios/agent-supervisor-scenarios.json, swissknife/test/unit/services/gui-optimizer/scenario-catalog.test.ts
- Interfaces: UiEvaluationScenario@1, DeterministicScenarioCatalog@1
- Conflict policy: Fixtures are inert and synthetic; do not contact live or production services.
- Preconditions: Agent Supervisor workflows and required viewport/state matrix are reviewed.
- Effects: Declares initial, loading, success, empty, recoverable/unrecoverable failure, invalid/valid submission, keyboard, mobile/desktop/wide, zoom, reduced motion, dark-mode-if-supported, unavailable-service, and confirmation-grant/deny scenarios.
- Evidence subset: Fixture digests, deterministic seed/time settings, scenario completeness table
- Acceptance: Scenarios have stable IDs, explicit fixtures, locale/color/viewport/text-scale inputs and expected terminal states; repeated catalog construction is byte-identical.

## VGO-009 Establish patch and browser-host security authority

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: security-authority
- Depends on: VGO-000
- Goal id: VGO-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/authority.py, external/ipfs_accelerate/test/api/test_gui_optimizer_authority.py
- Validation: PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ops/verified_gui_optimizer_vgo009_oracle.py --check-all && cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_authority.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/security-authority
- Parallel lane: vgo-lane-3
- Resource class: security-review
- Resource stage: authority
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/authority.py, external/ipfs_accelerate/test/api/test_gui_optimizer_authority.py
- Interfaces: GuiPatchAuthority@1, GuiHostBoundaryPolicy@1, GuiAcceptanceAuthority@1
- Conflict policy: Add a fail-closed optimizer authority wrapper without altering backend authorization, credentials, MCP execution, or the canonical browser gateway.
- Preconditions: SwissKnife gateway and mediator authority boundaries are recorded as canonical dependencies, not replaced; earlier candidates allowed string booleans, unknown or disguised browser fields, scope-only authority, stale or unbound policy evidence, caller-supplied decision overrides, caller fresh-policy fields without bound evidence, scalar and collection coercion, and alternate selectors; later false-greens authorized arbitrary matching digests, percent or double-encoded selectors, generic path-looking values, tuple collections, ten explicitly null scalar fields, and finally nested NaN, positive Infinity, and negative Infinity browser values despite their focused suites passing; the merged ca733399 candidate additionally accepted non-finite nested numbers, allowed public policy flags to disable mandatory scanning, retained adversarial built-in subclasses that hid selectors or forged binding comparisons, admitted relative traversal and drive-relative paths plus clear command/credential aliases, and treated direct null change kinds as an empty safe set; the next rejected draft also admitted sequence and string subclasses through direct patch-authority constructors, accepted Python Enum values at mapping wire fields, and accepted an AuthorityEvidence model instance inside a wire evidence array; its successor invoked a tuple subclass's truthiness before validating allowed_roots and invoked a dict subclass's attribute access before validating a wire evidence entry, so a raw subclass-controlled runtime exception could masquerade as safe rejection.
- Effects: Encodes allowed roots, forbidden change kinds, confirmation/action-binding review gates, fixture-only browser inputs, and evidence required for automatic acceptance.
- Evidence subset: Host-boundary tests, forbidden-path vectors, stale-policy and exact-confirmation doctrine, a uniquely named machine-counted WIRE_TYPE_CASES manifest containing exactly 221 unique cases with this exact decomposition: 13 string fields times {null, number, boolean, JSON array, JSON object} = 65, 16 boolean fields times {null, number, string, JSON array, JSON object} = 80, 6 JSON-array fields times {null, string, number, boolean, JSON object, Python tuple} = 36, BrowserHostInput.payload times {null, string, number, boolean, JSON array, non-dict Mapping or other non-JSON-object container} = 6, 3 digest fields times {uppercase, leading whitespace, trailing whitespace, other algorithm, short, long, empty, arbitrary equal noncanonical string} = 24, and exactly 10 recursive-shape cases {nested tuple, nested non-string object key, nested non-JSON container, nested NaN, nested positive Infinity, nested negative Infinity, adversarial dict subclass, adversarial list subclass, adversarial string value subclass, adversarial string key subclass} = 10; string fields are AuthorityEvidence.kind/evidence_id/binds_action_id/binds_argument_digest/policy_decision_id/notes, AcceptanceAuthorityRequest.intended_action_id/intended_argument_digest/browser_policy_outcome/policy_decision_id/confirmation_action_id/confirmation_argument_digest, and PatchPathClaim.path; boolean fields are AuthorityEvidence.valid/policy_fresh, AcceptanceAuthorityRequest.ui_visible/ui_enabled/browser_policy_authoritative_claim/policy_fresh/confirmation_required/confirmation_granted/accessibility_regression/security_regression, BrowserHostInput.fixture_only/uses_production_credentials/uses_production_services/uses_production_mcp_tools/uses_user_or_legal_data, and PatchPathClaim.declared; JSON-array fields are AcceptanceAuthorityRequest.change_kinds/evidence, BrowserHostInput.selected_host_paths/selected_commands/selected_executables, and PatchPathClaim.change_kinds; digest fields are AcceptanceAuthorityRequest.intended_argument_digest/confirmation_argument_digest and AuthorityEvidence.binds_argument_digest; a uniquely named machine-counted AUTHORIZATION_CASES manifest containing exactly 49 unique cases: the sealed baseline 27 plus mandatory unique IDs {auth:policy_configuration:path_scan_not_disableable, auth:policy_configuration:command_scan_not_disableable, auth:policy_configuration:credential_scan_not_disableable, auth:string_subclass_cannot_forge_action_or_digest_binding, auth:string_subclass_cannot_forge_confirmation_binding, auth:string_subclass_cannot_forge_nonempty_evidence_identity, auth:string_subclass_cannot_forge_policy_decision_binding, auth:value:generic_target_relative_traversal, auth:value:windows_drive_relative_path, auth:direct_patch_change_kinds_null, auth:value:cmd_without_exe, auth:value:powershell_exe, auth:value:shell_whitespace_and_metacharacters, auth:key:extended_credential_aliases, auth:direct_claims_sequence_subclass_rejected, auth:patch_allowed_roots_string_subclass_rejected, auth:wire_enum_evidence_kind_rejected, auth:wire_enum_patch_change_kind_rejected, auth:wire_enum_acceptance_change_kind_rejected, auth:wire_model_evidence_entry_rejected, auth:patch_allowed_roots_sequence_subclass_rejected_before_truthiness, auth:wire_evidence_dict_subclass_rejected_before_attribute_access}, strict-coercion and unknown-field vectors, all ten present-null scalar vectors, unbound caller policy-decision vectors, exact canonical sha256 digest grammar vectors, recursive JSON-shape and finite-number vectors, percent and double-encoded selector keys and values, disguised and alternate path/command/credential selectors including host_path_encoded, workingDirectoryEncoded, fileUriEncoded, credentialEncoded, generic target values, UNC and encoded Windows paths, encoded commands and credentials, hostFilePath, workingDirectory, cwd, fileUri, hostFilesystemPath, cmd, and credential, exact evidence-binding and freshness vectors, scope-not-authority vector, computed-decision override vectors, exact built-in JSON-type and canonical retained-tree vectors, unconditional policy-doctrine configuration vectors, string-subclass binding vectors, relative and percent-encoded traversal vectors, drive-relative Windows path vectors, cmd and powershell executable variants, tab/pipe/redirection shell vectors, and extended accessToken/authToken/clientSecret/privateKey/sessionToken/refreshToken/authorizationHeader/apiToken/oauthToken alias vectors, direct evaluate_claims sequence-subclass vector, patch allowed_roots string- and sequence-subclass vectors, mapping-wire Enum kind/change-kind vectors, mapping-wire model-instance evidence-entry vector, and mapping-wire dict-subclass evidence vector whose overridden attribute access raises if invoked
- Acceptance: UI state cannot synthesize authorization; browser content cannot select host paths, commands, or credentials; sensitive changes require contract verification or human review; missing or invalid authority evidence rejects safely; every mapping input is closed and strictly typed before coercion; mapping-wire decoders reject Python Enum and model/dataclass instances even when direct typed constructors support them, every evidence-array wire entry is an exact JSON object, and every change-kind wire entry is an exact built-in string, every present identifier, digest, outcome, and note field accepts only its declared string type, every collection field accepts only the declared JSON array or object type, Python tuples are not treated as JSON arrays, and strings, mappings, numbers, booleans, explicit null, and other containers never become valid values; recursive browser payloads admit only exact built-in RFC-JSON wire shapes at every depth, so nested arrays are exact lists, nested objects are exact string-key dictionaries with the same closed selector inspection, strings and numbers are exact built-ins, and every floating-point number is finite; nested NaN, positive Infinity, and negative Infinity reject; custom dict, list, str, numeric, mapping, or sequence subclasses cannot influence validation, traversal, binding, nonempty checks, allowed_roots normalization, or direct evaluate_claims processing and are rejected before any overridable method is invoked; in particular, allowed_roots is exact-type checked before truthiness or iteration and every wire evidence entry is exact-dict checked before attribute introspection, so subclass-controlled RuntimeError is a test failure rather than accepted rejection evidence; validation and selector scanning operate on the same recursively canonicalized retained tree; every accepted wire payload serializes with Python json.dumps using allow_nan=False and round-trips through json.loads without a custom encoder; omitted optional fields may default but present null must reject for AuthorityEvidence binds_action_id, binds_argument_digest, policy_decision_id, and notes and for AcceptanceAuthorityRequest intended_action_id, intended_argument_digest, browser_policy_outcome, policy_decision_id, confirmation_action_id, and confirmation_argument_digest; policy_decision_id or policy_fresh supplied by a caller has no authority without current evidence bound to the exact intended action and a canonical argument digest matching exactly sha256:[0-9a-f]{64}; uppercase hex, leading or trailing whitespace, other algorithm prefixes, short or long payloads, empty values, and arbitrary equal strings such as not-canonical never authorize; GuiHostBoundaryPolicy doctrine cannot be weakened through construction: forbid_absolute_path_strings and forbid_command_like_strings, if retained for compatibility, accept only literal True, False raises rather than silently becoming True, and path, command, and credential value inspection executes unconditionally; browser envelopes reject path, command, and credential selectors regardless of nesting, placement, casing, percent or double encoding, URI form, Windows form, or alternate spelling, including host_path_encoded with %2F or %252F values, encoded alias suffixes, generic target values that decode to paths, FILE URIs, UNC paths such as \\server\share, percent-encoded Windows paths such as C:%5Csecret or %5C%5Cserver%5Cshare, encoded commands such as cmd%2Eexe%20%2Fc, encoded credentials such as secret%3Atoken, relative traversal such as ../etc/passwd, .\\..\\secret, or their encoded forms, drive-relative paths such as C:secret, cmd or cmd.exe /c, powershell or powershell.exe commands, shell tabs, pipes, and redirections, and explicit credential aliases accessToken, authToken, clientSecret, privateKey, sessionToken, refreshToken, authorizationHeader, apiToken, and oauthToken; claim-derived change kinds and computed patch or host decisions override and cannot be replaced by acceptance input; authority evidence has a nonempty string identity and any evidence used to authorize an intended action is current and bound to that exact action and the same exact canonical argument digest; a scope declaration alone is never host authority; GuiPatchAuthority.evaluate_change_kinds rejects direct explicit null rather than interpreting it as an empty safe collection; the declared suite asserts WIRE_TYPE_CASES equals the exact field/category Cartesian products and ten recursive cases specified in Evidence subset with no omissions, substitutions, or padding, has exactly 221 unique IDs, and AUTHORIZATION_CASES has exactly 49 unique IDs including every mandatory ID specified in Evidence subset; each manifest entry executes exactly once and both pass with zero false accepts before completion.

## VGO-010 Implement canonical GUI content identity and provenance

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: identity
- Depends on: VGO-001, VGO-002
- Goal id: VGO-G020
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/identity.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity.py, swissknife/src/services/gui-optimizer/identity.ts, swissknife/test/unit/services/gui-optimizer/identity.test.ts
- Validation: cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_identity.py -q && cd ../../swissknife && npm run test:run -- test/unit/services/gui-optimizer/identity.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/content-identity
- Parallel lane: vgo-lane-3
- Resource class: cpu-small
- Resource stage: identity
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/identity.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity.py, swissknife/src/services/gui-optimizer/identity.ts, swissknife/test/unit/services/gui-optimizer/identity.test.ts
- Interfaces: GuiCanonicalIdentity@1, TypeScriptGuiCanonicalIdentity@1, UiComponentVersionCompiler@1, GuiArtifactDigest@1
- Conflict policy: Reuse committed canonical JSON and real CIDv1/SHA-256 primitives; do not create an alternative digest profile or CID-shaped text.
- Preconditions: Closed VGO identities exist and canonical identity behavior has been verified in datasets.
- Effects: Implements the same closed canonical identity profile in Python and TypeScript, binds stable logical identities separately from component versions, and includes normalized structure, props/types, state, handlers, accessibility, styles/tokens, actions, schema version, and extractor version.
- Evidence subset: Canonical byte vectors, CIDv1 decode/rehash checks, unrelated-edit and meaningful-edit identity cases
- Acceptance: Line movement and unrelated edits preserve stable identity; meaningful component material changes version identity; all identities rehash from retained canonical bytes and are domain separated.

## VGO-011 Build the typed UI dependency graph

- Status: pending
- Completion: auto
- No-change completion: forbidden
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: dependency-graph
- Depends on: VGO-002
- Goal id: VGO-G030
- Outputs: swissknife/src/services/gui-optimizer/component-graph.ts, swissknife/test/unit/services/gui-optimizer/component-graph.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/component-graph.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/dependency-graph
- Parallel lane: vgo-lane-0
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: swissknife/src/services/gui-optimizer/component-graph.ts, swissknife/test/unit/services/gui-optimizer/component-graph.test.ts
- Interfaces: UiComponentGraph@1, UiDependencyEdge@1, UiDependencyRelation@1
- Conflict policy: Consume scanner facts without editing scanner extraction rules; preserve unresolved dynamic edges explicitly.
- Preconditions: VGO-002 produces stable source findings with spans and confidence.
- Effects: Compiles renders, contains, routes_to, opens/closes_dialog, updates/reads_state, submits, validates, invokes_action, requires_confirmation, policy/schema/style/token/localization/test/screenshot/responsive/device edges.
- Evidence subset: Typed relation vectors, source-span fixtures, confidence and extractor-version assertions
- Acceptance: Every edge has source/target logical identity, finite relation, extraction method, confidence, extractor version and available span; unsupported targets remain unresolved rather than invented; the graph validation and completion receipt bind the exact accepted VGO-002 task CID and current scanner wire schema, so rescued output produced against a superseded scanner revision is never completion evidence.

## VGO-012 Build standalone GUI semantic capsules

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: semantic-capsules
- Depends on: VGO-001, VGO-002, VGO-010
- Goal id: VGO-G030
- Outputs: swissknife/src/services/gui-optimizer/ui-capsule.ts, swissknife/test/unit/services/gui-optimizer/ui-capsule.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/ui-capsule.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/gui-capsules
- Parallel lane: vgo-lane-2
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: swissknife/src/services/gui-optimizer/ui-capsule.ts, swissknife/test/unit/services/gui-optimizer/ui-capsule.test.ts
- Interfaces: UiSemanticCapsule@1, UiCapsuleCompiler@1, UiCompletenessBoundary@1
- Conflict policy: Implement the required standalone GUI capsule only; do not import any earlier semantic capsule or index subsystem.
- Preconditions: Closed wire models and scanner findings are available.
- Effects: Summarizes identity/version, purpose, props/events/state/states/transitions/actions/effects/bindings/confirmations, layout/responsiveness, keyboard/focus/a11y/localization, outcome states, dependencies/tests/screenshots, violations, unknowns, completeness, class and status.
- Evidence subset: Exact/conservative/heuristic/opaque fixtures, stale/integrity vectors, source-to-capsule traceability
- Acceptance: All required fields are present and bounded; evidence levels stay distinct; opaque/stale data cannot be reported verified; capsule bytes are deterministic for identical findings.

## VGO-016 Extract explicit bounded UI state machines

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: state-extraction
- Depends on: VGO-002, VGO-003
- Goal id: VGO-G040
- Outputs: swissknife/src/services/gui-optimizer/state-machine.ts, swissknife/test/unit/services/gui-optimizer/state-machine.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/state-machine.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/state-machine
- Parallel lane: vgo-lane-1
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: swissknife/src/services/gui-optimizer/state-machine.ts, swissknife/test/unit/services/gui-optimizer/state-machine.test.ts
- Interfaces: UiStateMachineExtractor@1, UiStateDefinition@1, UiEventDefinition@1, UiTransitionDefinition@1
- Conflict policy: Derive only source-supported states and explicit conservative unknowns; never fill missing transitions by intuition.
- Preconditions: Scanner findings and the deterministic scenario event vocabulary exist.
- Effects: Models initial/loading/ready/empty/success/failure/confirmation/disabled/offline/terminal/recovery states and click/submit/cancel/escape/keyboard/timeout/network/validation/confirmation/service events.
- Evidence subset: Reachability graphs, conditional-render spans, async handler fixtures, unresolved-transition reports
- Acceptance: Undefined destinations are rejected; explicit no-ops differ from absent outcomes; async effects expose observed loading/success/failure facts or a violation; extraction is deterministic.

## VGO-020 Adapt GUI states to existing bounded formal facilities

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-adapter
- Depends on: VGO-001, VGO-010, VGO-016
- Goal id: VGO-G040
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/formal_adapter.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_formal_adapter.py
- Validation: cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_formal_adapter.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/formal-adapter
- Parallel lane: vgo-lane-1
- Resource class: cpu-medium
- Resource stage: formalization
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/formal_adapter.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_formal_adapter.py
- Interfaces: GuiFormalAdapter@1, UiConstraintProblem@1, UiConstraintResult@1
- Conflict policy: Reuse the existing bounded state and SMT compiler boundary where practical; do not create a theorem-prover platform or cache proofs.
- Preconditions: Closed models, canonical identities, and extracted state-machine wire records are available.
- Effects: Translates finite UI state/action/form/modal/policy constraints into bounded solver or exact graph obligations with typed unavailable/unknown outcomes.
- Evidence subset: cvc5-compatible vectors, graph fallback results, solver-unavailable fail-closed cases, constraint-to-source provenance
- Acceptance: Results distinguish proved bounded property, counterexample, structural result, unavailable and unknown; no solver result asserts beauty, complete accessibility, complete security, or unbounded correctness.

## VGO-021 Implement the bounded UI invariant engine

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-invariants
- Depends on: VGO-001, VGO-016
- Goal id: VGO-G040
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/invariants.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_invariants.py
- Validation: cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_invariants.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/bounded-invariants
- Parallel lane: vgo-lane-3
- Resource class: cpu-medium
- Resource stage: formalization
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/invariants.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_invariants.py
- Interfaces: UiInvariantEngine@1, UiInvariantViolation@1, UiConstraintReceipt@1
- Conflict policy: Keep rules finite, explicit, source-traceable, and independent of aesthetic scoring or backend authorization.
- Preconditions: Closed UI records and state-machine event semantics exist.
- Effects: Checks state completeness/recovery/async outcomes/reachability, destructive confirmation, form labeling/error/submission/success, modal focus lifecycle, DOM identity/keyboard/headings/images, and policy-shaped interface obligations.
- Evidence subset: Satisfying models, minimal counterexamples, unsupported-property markers, rule identifiers and source bindings
- Acceptance: Every required bounded invariant has pass/fail/unknown semantics and counterexample evidence; uncertainty cannot authorize or auto-accept; documentation disclaims full accessibility/security proof.

## VGO-023 Validate policy and action bindings at the UI boundary

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: policy-bindings
- Depends on: VGO-009, VGO-011, VGO-016
- Goal id: VGO-G040
- Outputs: swissknife/src/services/gui-optimizer/policy-validator.ts, swissknife/test/unit/services/gui-optimizer/policy-validator.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/policy-validator.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/policy-validator
- Parallel lane: vgo-lane-2
- Resource class: security-review
- Resource stage: verification
- Implementation timeout seconds: 7200
- Predicted files: swissknife/src/services/gui-optimizer/policy-validator.ts, swissknife/test/unit/services/gui-optimizer/policy-validator.test.ts
- Interfaces: UiPolicyBindingValidator@1, UiActionBinding@1, UiConfirmationBinding@1
- Conflict policy: Read canonical action contracts, live-tool bindings and gateway/mediator behavior; do not modify or emulate authorization.
- Preconditions: Authority doctrine, typed graph and extracted action states exist.
- Effects: Checks one intended interface/method/schema per displayed action, current runtime re-evaluation, exact argument-bound confirmation, disabled/prohibited dispatch absence, and browser-host boundary use.
- Evidence subset: Canonical contract references, binding-source spans, stale-policy fixtures, hidden-handler and confirmation vectors
- Acceptance: Ambiguous/dynamic bindings are unresolved or review-required; UI visibility never proves permission; any dispatchable prohibited/disabled action or stale/exact-confirmation failure blocks automatic acceptance.

## VGO-027 Implement incremental GUI invalidation planning

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: invalidation
- Depends on: VGO-011, VGO-012, VGO-016
- Goal id: VGO-G050
- Outputs: swissknife/src/services/gui-optimizer/invalidation.ts, swissknife/test/unit/services/gui-optimizer/invalidation.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/invalidation.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/invalidation
- Parallel lane: vgo-lane-0
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: swissknife/src/services/gui-optimizer/invalidation.ts, swissknife/test/unit/services/gui-optimizer/invalidation.test.ts
- Interfaces: UiChangeSet@1, UiInvalidationPlanner@1, UiInvalidationPlan@1
- Conflict policy: Emit an explicit bounded plan; never rewrite or invalidate every application by default.
- Preconditions: Component graph, capsules, state machines, tests, screenshots and style/action/localization edges are available.
- Effects: Maps implementation, props/events, state, CSS/token, action-binding and localization changes to precise components, consumers, checks, scenarios, screenshots and escalation reasons.
- Evidence subset: Unrelated-style, design-token, contract, transition, binding and localization impact vectors
- Acceptance: Unrelated changes do not invalidate all screenshots; binding changes include policy/confirmation/host/interaction checks; state changes include reachability/outcome/formal checks; uncertainty explicitly requests broader fallback.

## VGO-030 Build compact, evidence-bounded GUI context packs

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: context-packs
- Depends on: VGO-010, VGO-012, VGO-027
- Goal id: VGO-G050
- Outputs: swissknife/src/services/gui-optimizer/context-pack.ts, swissknife/test/unit/services/gui-optimizer/context-pack.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/context-pack.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/context-pack
- Parallel lane: vgo-lane-3
- Resource class: cpu-medium
- Resource stage: context
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/context-pack.ts, swissknife/test/unit/services/gui-optimizer/context-pack.test.ts
- Interfaces: build_gui_context_pack@1, UiContextPack@1, UiContextTokenAccounting@1
- Conflict policy: Retrieve only declared target and dependency evidence; do not use a semantic index, model router, or unrelated raw repository dump.
- Preconditions: Canonical identities, capsules and an explicit invalidation plan exist.
- Effects: Packs objective, exact editable source/styles/tests, unchanged dependency capsules, state machine, failures, artifact references, routes/bindings, baseline, acceptance, exclusions, token estimates and escalation conditions.
- Evidence subset: Raw-source, capsule, screenshot-analysis, and source-tokens-replaced-by-capsules counts, total prompt estimate, ordinary-retrieval comparison, inclusion/exclusion reasons
- Acceptance: Editable, opaque, stale, unresolved or failure-point source is raw; stale capsules are rejected; budgets are bounded; compression accounting is reproducible; omitted context is explained without losing affected acceptance evidence.

## VGO-031 Implement live-DOM accessibility evaluation

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accessibility
- Depends on: VGO-003, VGO-012
- Goal id: VGO-G060
- Outputs: swissknife/src/services/gui-optimizer/accessibility.ts, swissknife/test/unit/services/gui-optimizer/accessibility.test.ts, swissknife/docs/gui-optimizer/ACCESSIBILITY_TOOLING_DECISION.md
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/accessibility.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/accessibility
- Parallel lane: vgo-lane-1
- Resource class: browser
- Resource stage: evaluation
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/accessibility.ts, swissknife/test/unit/services/gui-optimizer/accessibility.test.ts, swissknife/docs/gui-optimizer/ACCESSIBILITY_TOOLING_DECISION.md, swissknife/package.json, swissknife/package-lock.json, swissknife/yarn.lock
- Interfaces: UiAccessibilityEvaluator@1, AccessibilityReceipt@1, KeyboardEvaluation@1
- Conflict policy: Use existing browser/a11y facilities first; document whether they suffice before any change, and permit only one necessary exact direct accessibility dependency with synchronized committed locks.
- Preconditions: Deterministic scenario descriptors and accessibility contracts exist.
- Effects: Records the tooling necessity decision, and records automated severity, labels, keyboard reachability/order/traps, duplicate IDs, contrast, images/headings/forms, manual checks, unsupported WCAG criteria and screen-reader-review status.
- Evidence subset: Live-DOM findings, keyboard traces, tool/version identity, automation/manual boundary
- Acceptance: The decision records existing-facility coverage and, only if necessary, an exact pinned direct dependency and lock changes; receipts distinguish pass, violation, unsupported and manual review; automated tooling never claims full WCAG compliance; critical regressions are machine-readable acceptance blockers.

## VGO-032 Implement deterministic visual-regression receipts

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: visual-regression
- Depends on: VGO-003, VGO-010, VGO-012
- Goal id: VGO-G060
- Outputs: swissknife/src/services/gui-optimizer/visual-regression.ts, swissknife/test/unit/services/gui-optimizer/visual-regression.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/visual-regression.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/visual-regression
- Parallel lane: vgo-lane-0
- Resource class: browser
- Resource stage: evaluation
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/visual-regression.ts, swissknife/test/unit/services/gui-optimizer/visual-regression.test.ts
- Interfaces: VisualRegressionEvaluator@1, VisualRegressionReceipt@1, VisualDiffPolicy@1
- Conflict policy: Store real screenshot digests and measured diffs; never pass synthetic placeholders as captures or treat every pixel change as a regression.
- Preconditions: Scenario metadata, component identities and canonical artifact digests exist.
- Effects: Binds revision/scenario/viewport/scheme/locale/text scale/browser/version, before/after digests, dimensions, pixel/structural metrics, expected/forbidden regions, thresholds, approval and human-review need.
- Evidence subset: Deterministic image fixtures, pixel and structural metrics, threshold-boundary tests, artifact rehash
- Acceptance: Identical captures produce identical identities; unexplained and forbidden-region changes enforce configured gates; subjective appeal remains heuristic/human-reviewed; actual browser screenshots are distinguishable from simulations.

## VGO-034 Implement deterministic interaction and focus tracing

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: interaction-runner
- Depends on: VGO-003, VGO-016, VGO-023
- Goal id: VGO-G060
- Outputs: swissknife/src/services/gui-optimizer/interaction-runner.ts, swissknife/test/unit/services/gui-optimizer/interaction-runner.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/interaction-runner.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/interaction-runner
- Parallel lane: vgo-lane-2
- Resource class: browser
- Resource stage: evaluation
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/interaction-runner.ts, swissknife/test/unit/services/gui-optimizer/interaction-runner.test.ts
- Interfaces: UiInteractionRunner@1, InteractionReceipt@1, UiFocusTrace@1
- Conflict policy: Drive fixture scenarios through browser-visible interfaces only; never bypass policy, confirmation, or service boundaries to manufacture success.
- Preconditions: Scenario event vocabulary, state machines and action-binding validations exist.
- Effects: Captures state/event transitions, user and keyboard steps, reachability, focus moves/restoration/trapping, action dispatches, service outcomes and terminal result.
- Evidence subset: Timestamp-normalized traces, focus snapshots, action/method/schema references, terminal-state assertions
- Acceptance: Reruns with identical fixture inputs yield the same normalized trace identity; undefined transitions and focus loss are visible; confirmation grant/deny and unavailable/recovery paths remain distinct.

## VGO-040 Implement baseline and objective evaluator

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: evaluator
- Depends on: VGO-021, VGO-023, VGO-027, VGO-031, VGO-032, VGO-034
- Goal id: VGO-G060
- Outputs: swissknife/src/services/gui-optimizer/baseline.ts, swissknife/src/services/gui-optimizer/evaluator.ts, swissknife/test/unit/services/gui-optimizer/evaluator.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/evaluator.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/evaluator
- Parallel lane: vgo-lane-0
- Resource class: cpu-medium
- Resource stage: evaluation
- Implementation timeout seconds: 9000
- Predicted files: swissknife/src/services/gui-optimizer/baseline.ts, swissknife/src/services/gui-optimizer/evaluator.ts, swissknife/test/unit/services/gui-optimizer/evaluator.test.ts
- Interfaces: UiBaseline@1, GuiObjectiveEvaluator@1, UiMetricDelta@1, UiAcceptanceDecision@1
- Conflict policy: Objective metrics and hard invariants outrank subjective scores; no aesthetic gain can offset accessibility, policy, security or functional regression.
- Preconditions: Invariant, policy, invalidation, accessibility, visual and interaction evaluators produce typed evidence.
- Effects: Aggregates objective metrics, labels heuristic/human scores, compares one bounded objective, detects regression and returns accept/reject/human-review with reasons.
- Evidence subset: Metric normalization vectors, hard-gate precedence cases, deterministic-baseline identity tests
- Acceptance: Acceptance requires invariant preservation and declared measurable improvement; pixel change alone is neutral; unknown critical evidence prevents auto-accept; identical inputs produce identical baseline identity.

## VGO-041 Aggregate content-addressed GUI verification receipts

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: receipts
- Depends on: VGO-010, VGO-020, VGO-021, VGO-031, VGO-032, VGO-034, VGO-040
- Goal id: VGO-G020
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/receipts.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_receipts.py
- Validation: cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_receipts.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/receipts
- Parallel lane: vgo-lane-1
- Resource class: cpu-small
- Resource stage: evidence
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/gui_optimizer/receipts.py, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_receipts.py
- Interfaces: VisualRegressionReceipt@1, AccessibilityReceipt@1, InteractionReceipt@1, UiConstraintReceipt@1, GuiImprovementReceipt@1
- Conflict policy: Aggregate immutable evidence references without elevating simulation, integrity, structural, heuristic, or human claims beyond their declared authority.
- Preconditions: Canonical identity and typed evaluator receipt shapes are defined.
- Effects: Produces closed canonical receipt envelopes binding repository revision, scenario inputs, versions, before/after artifacts, patch scope, checks, metrics, decisions and evidence levels.
- Evidence subset: Canonical receipt vectors, missing/unknown-field rejection, nested artifact rehash, authority-label tests
- Acceptance: Complete accepted receipts contain all four verification receipt classes plus invalidation/context/patch evidence; rejected receipts preserve reasons; deterministic inputs produce deterministic receipt identity.

## VGO-043 Enforce bounded patch scope before execution

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: patch-scope
- Depends on: VGO-009, VGO-027
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/patch_scope.py, external/ipfs_accelerate/test/api/test_gui_optimizer_patch_scope.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_patch_scope.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/patch-scope
- Parallel lane: vgo-lane-2
- Resource class: security-review
- Resource stage: authority
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/patch_scope.py, external/ipfs_accelerate/test/api/test_gui_optimizer_patch_scope.py
- Interfaces: GuiPatchScopeGate@1, GuiImprovementProposal@1, GuiPatchScopeDecision@1
- Conflict policy: Fail closed on undeclared, unresolved, generated or excessive paths; never weaken repository safety or supervisor fencing.
- Preconditions: Optimizer authority and explicit invalidation records exist.
- Effects: Validates intended files/components/state/visual/test/screenshot declarations, path and line limits, diff semantics, action-contract evidence and forbidden mutations before applying a patch.
- Evidence subset: Out-of-scope diff fixtures, test-deletion and arbitrary-HTML vectors, file/line-limit cases, binding-change gates
- Acceptance: Undeclared files, unrelated applications, backend authority/credential changes, disabled security, deleted tests and unverified binding edits reject or require review with stable reason codes.

## VGO-045 Define a provider-neutral patch proposal interface

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: proposal-interface
- Depends on: VGO-009, VGO-030
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/proposal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_proposal.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_proposal.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/proposal-interface
- Parallel lane: vgo-lane-3
- Resource class: cpu-small
- Resource stage: orchestration
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/proposal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_proposal.py
- Interfaces: GuiPatchProposer@1, DeterministicGuiTransformation@1, HumanGuiReviewRequest@1
- Conflict policy: This is a dependency-injected provider interface, not model routing; it must not choose vendors or depend on any model-routing module.
- Preconditions: Closed context packs and security authority reason codes exist.
- Effects: Accepts deterministic, small/local, medium, frontier or human-provided proposals as typed inputs and records declared method/tier without hardcoding a vendor.
- Evidence subset: Deterministic label, deprecated-prop, design-token, ARIA-reference, exact route, and exact action-binding migrations; opaque/ambiguous/security escalation cases; provider exception fixtures
- Acceptance: Mechanical exact transformations remain deterministic; ambiguous, opaque, policy-bound or repeatedly failed requests escalate; provider absence cannot broaden scope or silently fabricate a patch.

## VGO-050 Apply proposals in isolated Git worktrees

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: worktree-execution
- Depends on: VGO-043
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/worktree_executor.py, external/ipfs_accelerate/test/api/test_gui_optimizer_worktree_executor.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_worktree_executor.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/worktree-executor
- Parallel lane: vgo-lane-1
- Resource class: io-medium
- Resource stage: execution
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/worktree_executor.py, external/ipfs_accelerate/test/api/test_gui_optimizer_worktree_executor.py
- Interfaces: GuiIsolatedWorktreeExecutor@1, GuiPatchApplicationReceipt@1
- Conflict policy: Reuse supervisor leases/fencing and explicit repositories; never accept browser paths, broad roots, destructive reset, or unchecked command strings.
- Preconditions: Patch scope passes and exact source revision/worktree parent is recorded.
- Effects: Creates a bounded isolated worktree, applies only the admitted patch, records the diff and cleanup state, and promotes nothing without later acceptance.
- Evidence subset: Temporary-repository fixtures, rejected-patch branch invariance, lease/fence failures, undeclared-file post-apply recheck
- Acceptance: Rejected or interrupted proposals cannot mutate the canonical branch; paths and subprocess operations are fixed by the host; resulting diff exactly matches the admitted scope.

## VGO-051 Select affected checks with uncertainty fallback

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: check-selection
- Depends on: VGO-027, VGO-040
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/check_plan.py, external/ipfs_accelerate/test/api/test_gui_optimizer_check_plan.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_check_plan.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/check-planning
- Parallel lane: vgo-lane-0
- Resource class: cpu-medium
- Resource stage: verification
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/check_plan.py, external/ipfs_accelerate/test/api/test_gui_optimizer_check_plan.py
- Interfaces: GuiAffectedCheckPlanner@1, GuiCheckPlan@1, GuiCheckExecutionReceipt@1
- Conflict policy: Commands come from a fixed repository-owned registry; browser input and proposals cannot inject subprocesses or suppress mandatory fallback.
- Preconditions: Invalidation and evaluator risk classifications exist.
- Effects: Orders direct unit/component/scenario checks first, then policy/host/browser/build or broader suites when graph confidence, dynamic behavior, shared tokens or failures require them.
- Evidence subset: Local-change precision vectors, uncertain-edge fallback cases, command allowlist tests, executed-check receipts
- Acceptance: Local changes avoid unrelated screenshots; uncertainty broadens verification predictably; action changes include policy/interaction/host tests; a failed required check blocks acceptance.

## VGO-053 Implement the bounded GUI improvement loop

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: improvement-loop
- Depends on: VGO-030, VGO-040, VGO-041, VGO-043, VGO-045, VGO-050, VGO-051, VGO-054
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/improvement_loop.py, external/ipfs_accelerate/test/api/test_gui_optimizer_improvement_loop.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_improvement_loop.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/improvement-loop
- Parallel lane: vgo-lane-2
- Resource class: cpu-medium
- Resource stage: orchestration
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/improvement_loop.py, external/ipfs_accelerate/test/api/test_gui_optimizer_improvement_loop.py
- Interfaces: VerifiedGuiOptimizer@1, GuiImprovementRun@1, GuiImprovementDecision@1
- Conflict policy: One or a few explicit objectives per bounded iteration; no whole-app aesthetic rewrite or automatic canonical merge.
- Preconditions: Context, baseline, receipt, scope and proposal contracts exist.
- Effects: Orchestrates baseline, objective/impact/context, proposal admission, isolated apply, rescan/invalidation, affected checks, fallback, metric comparison, decision and receipt.
- Evidence subset: Phase receipts, bounded-attempt tests, acceptance/rejection/human-review transitions, no-canonical-mutation checks
- Acceptance: Every phase is explicit and resumable by stable run ID; acceptance requires improved target metric plus all hard gates; missing evidence rejects or reviews; receipts exist for every terminal decision.

## VGO-054 Persist interruption-safe improvement journals

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: run-journal
- Depends on: VGO-041, VGO-043
- Goal id: VGO-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/run_journal.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/artifact_store.py, external/ipfs_accelerate/test/api/test_gui_optimizer_run_journal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_artifact_store.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_run_journal.py test/api/test_gui_optimizer_artifact_store.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/run-journal
- Parallel lane: vgo-lane-3
- Resource class: io-medium
- Resource stage: resilience
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/run_journal.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/artifact_store.py, external/ipfs_accelerate/test/api/test_gui_optimizer_run_journal.py, external/ipfs_accelerate/test/api/test_gui_optimizer_artifact_store.py
- Interfaces: GuiRunJournal@1, GuiRunCheckpoint@1, GuiResumeDecision@1, GuiEvidenceArtifactStore@1
- Conflict policy: Append immutable phase records and artifact manifests atomically; this evidence CAS is not a proof cache and accepts no browser-selected path; never infer completion from process exit or reuse stale/foreign worktree state.
- Preconditions: Canonical receipts and scope/run identities exist.
- Effects: Persists content-addressed checkpoints and screenshot/trace/accessibility artifacts under a host-owned allowlisted runtime root, records heartbeat/progress/worktree/attempt, verifies resume preconditions, and chooses resume/restart/reject safely.
- Evidence subset: Artifact byte rehash and path-escape tests, kill/restart fixtures, truncated/corrupt journal cases, revision mismatch and idempotent rerun tests
- Acceptance: Artifact bytes resolve only through verified CIDs and fixed host roots; interrupted runs resume without duplicate effect or canonical mutation; corrupt/stale/mismatched state fails closed; identical completed runs return the same terminal receipt identity.

## VGO-060 Expose the standalone `gui-opt` development CLI

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: cli
- Depends on: VGO-050, VGO-051, VGO-053, VGO-054
- Goal id: VGO-G080
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/cli.py, external/ipfs_accelerate/test/api/test_gui_optimizer_cli.py, swissknife/src/services/gui-optimizer/cli.ts, swissknife/test/unit/services/gui-optimizer/cli.test.ts, scripts/gui-opt
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_cli.py -q && cd ../../swissknife && npm run test:run -- test/unit/services/gui-optimizer/cli.test.ts && cd .. && scripts/gui-opt --help
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/cli
- Parallel lane: vgo-lane-0
- Resource class: cpu-small
- Resource stage: integration
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/cli.py, external/ipfs_accelerate/test/api/test_gui_optimizer_cli.py, swissknife/src/services/gui-optimizer/cli.ts, swissknife/test/unit/services/gui-optimizer/cli.test.ts, scripts/gui-opt
- Interfaces: GuiOptimizerTypeScriptCliBridge@1, gui-opt scan@1, gui-opt baseline@1, gui-opt impact@1, gui-opt evaluate@1, gui-opt pack-context@1, gui-opt verify@1, gui-opt improve@1, gui-opt report@1
- Conflict policy: Root script is a narrow fixed adapter; CLI target IDs resolve through a repository registry and cannot select arbitrary paths or commands.
- Preconditions: Worktree, check-plan, improvement-loop and journal services are available.
- Effects: Provides a fixed Python/TypeScript bridge and all required scan/baseline/impact/evaluate/context/verify/improve/report commands with sealed PYTHONPATH/toolchain setup, fixed target/check registries (including the named target and current-tree verification aliases used below), explicit durable-receipt arguments, JSON receipts and nonzero fail-closed exits.
- Evidence subset: CLI help/schema snapshots, fixed-target resolution tests, malformed/path-injection cases, interrupted-report recovery
- Acceptance: Commands are deterministic and scriptable; no production/effectful defaults exist; verify/improve operate only in isolated worktrees; report resolves immutable run evidence.

## VGO-061 Create controlled Agent Supervisor browser fixtures

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: target-fixtures
- Depends on: VGO-003, VGO-031, VGO-032, VGO-034
- Goal id: VGO-G090
- Outputs: swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-host.html, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-services.js, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-scenarios.json, swissknife/test/unit/services/gui-optimizer/agent-supervisor-fixtures.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/agent-supervisor-fixtures.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/target-fixtures
- Parallel lane: vgo-lane-3
- Resource class: browser
- Resource stage: fixtures
- Implementation timeout seconds: 9000
- Predicted files: swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-host.html, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-services.js, swissknife/test/fixtures/gui-optimizer/agent-supervisor/fixture-scenarios.json, swissknife/test/unit/services/gui-optimizer/agent-supervisor-fixtures.test.ts
- Interfaces: AgentSupervisorFixtureHost@1, AgentSupervisorFixtureServices@1
- Conflict policy: Mirror public live interfaces with inert deterministic fakes; never copy credentials, call live services, invoke MCP tools, or weaken the production gateway.
- Preconditions: Evaluation contracts define all target scenarios and evidence inputs.
- Effects: Controls time, IDs, supervisor/governed-service results, loading/errors/empty data/confirmations and view preferences for repeatable browser runs.
- Evidence subset: Fixture purity tests, no-network canary, deterministic response and seed snapshots
- Acceptance: Required scenarios are reproducible without production state; unexpected network/effectful calls fail; fixtures cannot issue an authoritative allow decision.

## VGO-062 Record the Agent Supervisor semantic baseline

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: target-semantic-baseline
- Depends on: VGO-011, VGO-012, VGO-016, VGO-020, VGO-021, VGO-023, VGO-027, VGO-040, VGO-041
- Goal id: VGO-G090
- Outputs: swissknife/src/services/gui-optimizer/targets/agent-supervisor.ts, swissknife/test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-semantic-baseline.json
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/target-semantic-baseline
- Parallel lane: vgo-lane-2
- Resource class: cpu-medium
- Resource stage: baseline
- Implementation timeout seconds: 10800
- Predicted files: swissknife/src/services/gui-optimizer/targets/agent-supervisor.ts, swissknife/test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-semantic-baseline.json
- Interfaces: AgentSupervisorTarget@1, UiSemanticBaseline@1
- Conflict policy: Analyze only committed live source/manifest/routes/contracts/tests; document legacy/manual duplication but do not rewrite it in this task.
- Preconditions: Scanner, graph, capsule, state, invariant, policy, invalidation and evaluator layers are integrated.
- Effects: Records exact application/screen/component identities, graph/state statistics, source/test/action/style dependencies, violations, unresolved dynamics, completeness and current revision.
- Evidence subset: Canonical source inventory, scanner output, graph/state receipts, baseline violations and known pre-change failures
- Acceptance: Baseline identifies `swissknife/web/js/apps/agent-supervisor.js` as live target, distinguishes canonical/legacy surfaces, contains no unearned verified claims, and is identical on deterministic rerun.

## VGO-068 Capture the live Agent Supervisor browser baseline

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: target-browser-baseline
- Depends on: VGO-003, VGO-031, VGO-032, VGO-034, VGO-040, VGO-061, VGO-062
- Goal id: VGO-G090
- Outputs: swissknife/build-tools/configs/playwright.verified-gui-optimizer.config.ts, swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-baseline.spec.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline-artifacts.json
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/agent-supervisor-console.spec.ts test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts test/e2e/verified-gui-optimizer-agent-supervisor-baseline.spec.ts --reporter=line
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/target-browser-baseline
- Parallel lane: vgo-lane-1
- Resource class: browser
- Resource stage: baseline
- Implementation timeout seconds: 14400
- Predicted files: swissknife/build-tools/configs/playwright.verified-gui-optimizer.config.ts, swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-baseline.spec.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-browser-baseline-artifacts.json
- Interfaces: AgentSupervisorBrowserBaseline@1, AccessibilityReceipt@1, VisualRegressionReceipt@1, InteractionReceipt@1
- Conflict policy: Capture current behavior without editing target implementation or approving visual heuristics; use controlled fixture services only. This task exclusively owns the optimizer Playwright config, which selects only declared VGO/Agent Supervisor specs, launches the installed full Chromium through `channel: 'chromium'`, uses a stable path-derived noncolliding port, and sets `reuseExistingServer: false`.
- Preconditions: Existing controlled Agent Supervisor console fixtures plus deterministic scenario, semantic baseline and live evaluation adapters exist; the sealed Node 22 toolchain and installed Playwright runner are available.
- Effects: Runs the existing console and goal/task lifecycle checks plus required viewport/state/keyboard/confirmation/unavailable scenarios, records real screenshots, DOM/a11y results, interaction/focus traces, overflow/clipping and objective metrics, stores raw artifacts in the VGO-054 host-owned CAS, and commits their closed durable manifest and baseline receipt.
- Evidence subset: Screenshot digests and dimensions, browser/version metadata, automated/manual a11y boundary, normalized interaction traces
- Acceptance: The dedicated config actually discovers every named spec and uses installed full Chromium without a headless-shell download; screenshot, trace and accessibility artifact CIDs resolve and rehash through the durable manifest; deterministic rerun identities match; baseline problems are reported rather than hidden; no production service or credentials are used; unsupported/manual review items remain explicit.

## VGO-070 Add static-analysis, invalidation, and context fixtures

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: static-fixtures
- Depends on: VGO-030, VGO-062
- Goal id: VGO-G080
- Outputs: swissknife/test/fixtures/gui-optimizer/static/unrelated-style.css, swissknife/test/fixtures/gui-optimizer/static/changed-token.css, swissknife/test/fixtures/gui-optimizer/static/opaque-component.ts, swissknife/test/fixtures/gui-optimizer/static/stale-capsule.json, swissknife/test/unit/services/gui-optimizer/static-impact-context.test.ts
- Validation: cd swissknife && npm run test:run -- test/unit/services/gui-optimizer/static-impact-context.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/static-fixtures
- Parallel lane: vgo-lane-1
- Resource class: cpu-medium
- Resource stage: fixtures
- Implementation timeout seconds: 9000
- Predicted files: swissknife/test/fixtures/gui-optimizer/static/unrelated-style.css, swissknife/test/fixtures/gui-optimizer/static/changed-token.css, swissknife/test/fixtures/gui-optimizer/static/opaque-component.ts, swissknife/test/fixtures/gui-optimizer/static/stale-capsule.json, swissknife/test/unit/services/gui-optimizer/static-impact-context.test.ts
- Interfaces: GuiStaticFixtureSuite@1, UiInvalidationPlan@1, UiContextPack@1
- Conflict policy: Add controlled fixtures and integration assertions only; do not modify production scanner/evaluator behavior to fit fixtures.
- Preconditions: Context packing and target semantic baseline are available.
- Effects: Exercises stale and opaque components, unrelated styles, changed tokens, state/binding changes, source inclusion rules, token accounting and bounded impact.
- Evidence subset: Fixture identities, expected affected nodes/scenarios/checks, raw-source inclusion and compression metrics
- Acceptance: Opaque forces raw source; stale capsules cannot be consumed; unrelated style avoids global screenshots; token/action/state changes invalidate only their declared dependent evidence plus uncertainty fallback.

## VGO-071 Add formal, form, modal, policy, and security fixtures

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: formal-security-fixtures
- Depends on: VGO-021, VGO-023, VGO-043, VGO-062
- Goal id: VGO-G080
- Outputs: external/ipfs_accelerate/test/fixtures/gui_optimizer/formal-security-cases.json, external/ipfs_accelerate/test/api/test_gui_optimizer_formal_security_fixtures.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_formal_security_fixtures.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/formal-security-fixtures
- Parallel lane: vgo-lane-2
- Resource class: security-review
- Resource stage: fixtures
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/test/fixtures/gui_optimizer/formal-security-cases.json, external/ipfs_accelerate/test/api/test_gui_optimizer_formal_security_fixtures.py
- Interfaces: GuiFormalSecurityFixtureSuite@1, UiConstraintReceipt@1, GuiPatchScopeDecision@1
- Conflict policy: Fixtures may model attacks but never execute production tools, credentials, remote scripts, arbitrary HTML, paths or commands.
- Preconditions: Invariant, binding and patch-scope gates plus target semantic state are available.
- Effects: Covers unlabeled input, missing error association, inaccessible custom control, broken modal focus, duplicate IDs, missing async failure, unconfirmed destruction, disabled dispatch, stale policy and confirmation mismatch.
- Evidence subset: Minimal counterexamples, reason codes, state/action/form source bindings, accepted/rejected fixture decisions
- Acceptance: Every required failure is detected; accessibility and confirmation/security regressions block automatic acceptance; visibility/enabled state never authorizes; unsupported proof claims remain unknown/review-required.

## VGO-072 Add browser, responsive, visual, and accessibility fixtures

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: browser-fixtures
- Depends on: VGO-031, VGO-032, VGO-034, VGO-061, VGO-068
- Goal id: VGO-G080
- Outputs: swissknife/test/fixtures/gui-optimizer/browser/a11y-visual-cases.json, swissknife/test/e2e/verified-gui-optimizer-fixtures.spec.ts
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/verified-gui-optimizer-fixtures.spec.ts --reporter=line
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/browser-fixtures
- Parallel lane: vgo-lane-0
- Resource class: browser
- Resource stage: fixtures
- Implementation timeout seconds: 14400
- Predicted files: swissknife/test/fixtures/gui-optimizer/browser/a11y-visual-cases.json, swissknife/test/e2e/verified-gui-optimizer-fixtures.spec.ts
- Interfaces: GuiBrowserFixtureSuite@1, AccessibilityReceipt@1, VisualRegressionReceipt@1, InteractionReceipt@1
- Conflict policy: Drive deterministic fixture pages only and retain raw failing evidence; no snapshot update may auto-approve a regression.
- Preconditions: Live evaluators, controlled services and a current target browser baseline exist.
- Effects: Covers narrow overflow, localized clipping, focus lifecycle, keyboard navigation, contrast/labels/IDs, expected/forbidden visual regions, visual gain with a11y regression, and click reduction that bypasses confirmation; raw screenshot, trace, and accessibility artifacts are persisted through the VGO-054 store and referenced by CID from test receipts.
- Evidence subset: Before/after screenshots, DOM findings, focus/interaction traces, viewport/locale/text-scale/browser metadata
- Acceptance: The dedicated optimizer config executes the fixture spec in installed full Chromium; artifact CIDs resolve and rehash; overflow/clipping and focus failures are measurable; a11y/security regressions override visual/click gains; pixel difference is classified through region/threshold/evidence policy, not assumed regression.

## VGO-075 Prove cross-language deterministic GUI identities

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: identity-conformance
- Depends on: VGO-010, VGO-012, VGO-041, VGO-062
- Goal id: VGO-G080
- Outputs: external/ipfs_datasets/tests/fixtures/gui_optimizer/identity-vectors.json, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity_vectors.py, swissknife/test/fixtures/gui-optimizer/identity-vectors.json, swissknife/test/unit/services/gui-optimizer/identity-vectors.test.ts
- Validation: cmp external/ipfs_datasets/tests/fixtures/gui_optimizer/identity-vectors.json swissknife/test/fixtures/gui-optimizer/identity-vectors.json && cd external/ipfs_datasets && python3 -m pytest tests/unit/logic/gui_optimizer/test_identity_vectors.py -q && cd ../../swissknife && npm run test:run -- test/unit/services/gui-optimizer/identity-vectors.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/identity-conformance
- Parallel lane: vgo-lane-3
- Resource class: cpu-small
- Resource stage: conformance
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_datasets/tests/fixtures/gui_optimizer/identity-vectors.json, external/ipfs_datasets/tests/unit/logic/gui_optimizer/test_identity_vectors.py, swissknife/test/fixtures/gui-optimizer/identity-vectors.json, swissknife/test/unit/services/gui-optimizer/identity-vectors.test.ts
- Interfaces: GuiIdentityConformanceVectors@1, GuiCanonicalIdentity@1, UiComponentVersion@1, GuiImprovementReceipt@1
- Conflict policy: Duplicate only the reviewed golden vector bytes in both submodules; implementations may not special-case vector values or weaken canonical profiles. Commit both nested repositories first, validate both runtimes, then stage both exact gitlinks in one atomic superproject handoff with both nested worktrees clean.
- Preconditions: Python identities, TypeScript capsules and canonical receipt envelopes exist.
- Effects: Verifies the byte-identical shared vectors and stable/application/screen/component/version/baseline/receipt identities in both Python and TypeScript runtimes, including Unicode normalization, key ordering, domain separation, rehash and negative cases.
- Evidence subset: Byte-identical vector copies, decoded CID multicodec/multihash, SHA-256 digests, mutation matrix
- Acceptance: The two checked-in vector files compare byte-for-byte and both runtime suites pass; both runtimes produce exact expected canonical bytes and real identities; identical sources/scenarios yield identical baselines; any bound material mutation changes the appropriate identity and not unrelated stable identity.

## VGO-080 Apply the bounded focus and error-association target patch

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: target-improvement
- Depends on: VGO-023, VGO-031, VGO-034, VGO-043, VGO-060, VGO-068, VGO-071, VGO-072, VGO-075, VGO-086
- Goal id: VGO-G090
- Outputs: swissknife/web/js/apps/agent-supervisor.js, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-proposal.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-improvement-receipt.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-artifacts.json
- Validation: scripts/gui-opt verify agent-supervisor-target --receipt implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-improvement-receipt.json && cd swissknife && npm run test:run -- test/browser/agent-supervisor-console-gateway.test.ts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/target-patch
- Parallel lane: vgo-lane-2
- Resource class: browser
- Resource stage: implementation
- Implementation timeout seconds: 10800
- Predicted files: swissknife/web/js/apps/agent-supervisor.js, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-proposal.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-improvement-receipt.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-target-artifacts.json
- Interfaces: AgentSupervisorWindow@current, AgentSupervisorSteeringForm@current, AgentSupervisorDispatchForm@current
- Conflict policy: The admitted source patch may touch only the declared live Agent Supervisor file; the task additionally owns only its three declared durable evidence files. Preserve service contracts, exact confirmation tokens, gateway calls, authorization, credentials, routes and unrelated applications. Commit the accepted SwissKnife change first and stage its exact gitlink together with the root evidence in one atomic superproject handoff.
- Preconditions: Current semantic/browser baselines identify reproducible focus loss and form error-association objective failures; patch scope and adversarial gates admit the proposal; the integrated `gui-opt` loop and identity conformance are available.
- Effects: Runs the one-objective improvement through `gui-opt` in an isolated worktree, preserves or restores initiating/active focus across bounded rerenders, binds steering/dispatch validation messages and invalid/disabled semantics to their exact controls without bypassing confirmation, rescans and calculates invalidations, executes affected checks with uncertainty fallback, compares metrics, and records the proposal, terminal receipt, and CAS artifact manifest before any accepted handoff.
- Evidence subset: Declared proposal, source diff, focus traces, form accessible-name/error bindings, confirmation grant/deny and service invocation traces
- Acceptance: `gui-opt verify` rehashes the proposal, before/after artifact CIDs and complete improvement receipt; the declared focus-loss and error-association metrics improve; keyboard behavior, action reachability and exact confirmations remain correct; no policy/binding/security/accessibility regression occurs; undeclared changes or missing evidence reject or require review, and a rejected proposal leaves the canonical branch unchanged.

## VGO-081 Add Agent Supervisor target regression tests

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: target-regression
- Depends on: VGO-062, VGO-068, VGO-070, VGO-071, VGO-072, VGO-080
- Goal id: VGO-G090
- Outputs: swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts, swissknife/test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-regression-receipt.json
- Validation: cd swissknife && npm run test:run -- test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts --reporter=line
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/target-regression
- Parallel lane: vgo-lane-3
- Resource class: browser
- Resource stage: verification
- Implementation timeout seconds: 10800
- Predicted files: swissknife/test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts, swissknife/test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-regression-receipt.json
- Interfaces: AgentSupervisorRegressionSuite@1, AllAppToolGateway@current, GovernedActionLifecycle@current
- Conflict policy: Add tests and the declared durable regression receipt without deleting, weakening, skipping or rewriting existing gateway/lifecycle assertions and without owning the target implementation file or Playwright config.
- Preconditions: The original target baselines, accepted bounded patch and controlled formal/browser fixture suites exist.
- Effects: Compares the VGO-068 pre-change defect evidence with the current target, then locks focus/error contracts, loading/error/empty outcomes, keyboard path, exact confirmations, disabled dispatch behavior, gateway boundaries and responsive overflow expectations in direct browser and dedicated-config Playwright tests.
- Evidence subset: Direct browser boundary assertions, deterministic Playwright scenario traces, existing lifecycle-suite references
- Acceptance: The archived baseline demonstrates the original defects, the current implementation passes both named suites in installed full Chromium, targeted mutation/adversarial vectors fail for focus, association, confirmation and policy regressions, the durable receipt rehashes its artifacts, and tests never use real services or browser-generated authorization.

## VGO-083 Define exactly 15 controlled improvement benchmark tasks

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: benchmark-catalog
- Depends on: VGO-060, VGO-062, VGO-068, VGO-070, VGO-072, VGO-075
- Goal id: VGO-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/benchmark.py, external/ipfs_accelerate/test/fixtures/gui_optimizer/benchmark-tasks.json, external/ipfs_accelerate/test/api/test_gui_optimizer_benchmark_catalog.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_benchmark_catalog.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/benchmark-catalog
- Parallel lane: vgo-lane-1
- Resource class: cpu-medium
- Resource stage: benchmark
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/gui_optimizer/benchmark.py, external/ipfs_accelerate/test/fixtures/gui_optimizer/benchmark-tasks.json, external/ipfs_accelerate/test/api/test_gui_optimizer_benchmark_catalog.py
- Interfaces: GuiOptimizationBenchmark@1, GuiBenchmarkTask@1, GuiBenchmarkResult@1
- Conflict policy: Benchmark only the selected screen and controlled variants; do not ask a provider to make the app generally better or auto-approve subjective redesigns.
- Preconditions: CLI, target baselines, fixtures and identity conformance are complete.
- Effects: Defines exactly 15 uniquely identified bounded tasks covering focus restoration, accessible labels, error presentation, loading state, failure state, interaction-step reduction, responsive overflow, primary-action hierarchy, design-token consistency, confirmation UX, empty-state guidance, keyboard reachability, localization clipping, modal focus lifecycle, and action-binding integrity, each with an expected route and evidence class.
- Evidence subset: Exactly 15 per-task baseline/reference IDs, raw-retrieval token estimates, expected affected components/scenarios/checks, and deterministic method or declared provider tier
- Acceptance: The catalog test rejects any count other than 15 and duplicate IDs; every task has one/few measurable objectives, bounded files, controlled fixtures, hard gates and expected decision type; rerunning catalog creation is byte-identical.

## VGO-086 Prove adversarial patch acceptance and isolation

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: adversarial-acceptance
- Depends on: VGO-043, VGO-050, VGO-051, VGO-053, VGO-054, VGO-060, VGO-070, VGO-071, VGO-072
- Goal id: VGO-G100
- Outputs: external/ipfs_accelerate/test/fixtures/gui_optimizer/adversarial-proposals.json, external/ipfs_accelerate/test/api/test_gui_optimizer_acceptance_adversarial.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_acceptance_adversarial.py -q
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/adversarial-acceptance
- Parallel lane: vgo-lane-0
- Resource class: security-review
- Resource stage: verification
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/fixtures/gui_optimizer/adversarial-proposals.json, external/ipfs_accelerate/test/api/test_gui_optimizer_acceptance_adversarial.py
- Interfaces: GuiPatchScopeGate@1, GuiAcceptanceDecision@1, GuiIsolatedWorktreeExecutor@1
- Conflict policy: Attack fixtures remain data and temporary-repository diffs; never execute their HTML, commands, tools, paths or credential payloads.
- Preconditions: Scope, isolated-worktree, check, journal, loop, CLI and controlled verification fixture contracts exist.
- Effects: Exercises out-of-scope edits, test deletion, arbitrary HTML, authority/credential/check weakening, unrelated apps, excess size, unverified binding changes, aesthetic-a11y regressions, click-confirmation bypass, interrupted optimization and deterministic rerun paths, stale journal recovery, and rejected-patch canonical-branch isolation through the integrated executor and acceptance loop.
- Evidence subset: Stable rejection codes, canonical-branch trees before/after, hard-gate precedence, complete rejected receipts
- Acceptance: All forbidden proposals reject or require review with complete reason-coded receipts; critical accessibility and authorization/confirmation regressions are never auto-accepted; rejected, interrupted and resumed runs are covered; rejection and interruption leave the canonical branch byte-identical; a deterministic rerun returns the same terminal identity.

## VGO-090 Execute and report the controlled benchmark

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: benchmark-execution
- Depends on: VGO-060, VGO-080, VGO-081, VGO-083, VGO-086
- Goal id: VGO-G100
- Outputs: implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.md, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark-artifacts.json
- Validation: scripts/gui-opt evaluate agent-supervisor --benchmark benchmark-v1 --expected-tasks 15 --progress-interval-seconds 60 && scripts/gui-opt report benchmark-agent-supervisor --require-complete --expected-tasks 15 --verify-receipts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/benchmark-run
- Parallel lane: vgo-lane-3
- Resource class: browser
- Resource stage: benchmark
- Implementation timeout seconds: 14400
- Predicted files: implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.json, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark.md, implementation_plan/evidence/verified_gui_optimizer/agent-supervisor-benchmark-artifacts.json
- Interfaces: GuiOptimizationBenchmark@1, GuiBenchmarkResult@1, GuiImprovementReceipt@1
- Conflict policy: Report actual outcomes including failures and unmet targets; benchmark execution cannot modify the canonical branch except through separately admitted accepted patches.
- Preconditions: Target patch/regression evidence, the exact 15-task benchmark catalog, durable artifact store and adversarial gates are integrated.
- Effects: Runs all 15 controlled tasks through the integrated improvement loop, journals each bounded phase and emits progress at intervals below the supervisor stall threshold, resumes interruption-safe work by run identity, and records baseline violations/screenshots, impact, raw/context tokens, proposals, checks, changed screenshots, before/after metrics, accessibility/steps, decision, regressions and route/method; artifact bytes remain in the host-owned CAS and the durable manifest binds every referenced CID.
- Evidence subset: Exactly 15 complete task receipts, aggregate statistics, deterministic rerun IDs, artifact manifest, and failed/review-required cases
- Acceptance: Fail-closed reporting verifies exactly 15 terminal task receipts and every artifact CID; the report includes actual median context reduction, invalidation precision, decision/route distribution and target attainment; zero critical accessibility or authorization/confirmation regressions are automatically accepted; unmet 30% context or other targets are disclosed rather than hidden.

## VGO-091 Audit acceptance, policy, and security evidence

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: acceptance-audit
- Depends on: VGO-080, VGO-081, VGO-086, VGO-090
- Goal id: VGO-G100
- Outputs: implementation_plan/evidence/verified_gui_optimizer/acceptance-security-audit.json
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_authority.py test/api/test_gui_optimizer_patch_scope.py test/api/test_gui_optimizer_acceptance_adversarial.py -q && cd ../../swissknife && npm run test:run -- test/unit/services/gui-optimizer/policy-validator.test.ts test/browser/all-app-tool-gateway.test.ts test/browser/agent-supervisor-console-gateway.test.ts test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.verified-gui-optimizer.config.ts test/e2e/agent-supervisor-goal-task-lifecycle.spec.ts test/e2e/verified-gui-optimizer-agent-supervisor-regression.spec.ts --reporter=line && cd .. && scripts/gui-opt report acceptance-security-audit --require-complete --verify-receipts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/security-audit
- Parallel lane: vgo-lane-2
- Resource class: security-review
- Resource stage: audit
- Implementation timeout seconds: 10800
- Predicted files: implementation_plan/evidence/verified_gui_optimizer/acceptance-security-audit.json
- Interfaces: GuiAcceptanceAuthority@1, UiPolicyBindingValidator@1, GuiSecurityAuditReceipt@1
- Conflict policy: Read and report current-tree evidence only; do not change backend policy, credential handling, gateways, target implementation, tests or benchmark results.
- Preconditions: Target patch, benchmark decisions, durable receipts and regression/adversarial suites are integrated at the exact audited source revision.
- Effects: Replays authority, confirmation, binding, scope, accessibility-hard-gate and canonical-branch isolation claims across Python, TypeScript gateway and full-browser suites; audits every automatically accepted benchmark decision; rehashes referenced evidence; and records gaps or counterexamples in the durable audit receipt.
- Evidence subset: Exact revision, commands/results, action/schema/confirmation bindings, rejected-patch tree comparisons, claim-level authority labels
- Acceptance: Every named suite and fail-closed receipt check passes; no UI authorization synthesis, hidden prohibited dispatch, confirmation bypass, credential/host escape or auto-accepted critical accessibility regression is found; every accepted benchmark task is covered; any evidence gap blocks closeout and is reported without a security-proof overclaim.

## VGO-093 Run full current-tree build and browser verification

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: integration-verification
- Depends on: VGO-060, VGO-075, VGO-080, VGO-081, VGO-086, VGO-090, VGO-091, VGO-096
- Goal id: VGO-G100
- Outputs: implementation_plan/evidence/verified_gui_optimizer/current-tree-verification.json
- Validation: scripts/gui-opt verify current-tree --full --receipt implementation_plan/evidence/verified_gui_optimizer/current-tree-verification.json
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/current-tree-verification
- Parallel lane: vgo-lane-0
- Resource class: browser
- Resource stage: verification
- Implementation timeout seconds: 14400
- Predicted files: implementation_plan/evidence/verified_gui_optimizer/current-tree-verification.json
- Interfaces: VerifiedGuiOptimizer@1, SwissKnifeWebBuild@current, AgentSupervisorRegressionSuite@1
- Conflict policy: Verification is non-mutating except its declared durable receipt. The CLI creates a disposable isolated verification worktree, runs all generators/builds there, discards generated `dist`, Playwright, coverage, bundle-budget and freshness-audit outputs, and never refreshes baselines to hide failures or edits code/tests while reporting.
- Preconditions: All three submodule implementations and documentation, CLI, benchmark/security receipts, conformance vectors, target patch and regression/adversarial suites are integrated; the outer source worktree is clean apart from the declared receipt destination.
- Effects: In one disposable worktree, runs datasets and accelerator GUI optimizer test groups, SwissKnife optimizer unit/browser suites, dedicated-config target Playwright/gateway/lifecycle checks in full Chromium, both identity-conformance runtimes, CLI smoke, affected-plus-uncertainty-fallback selection, boundary/import exclusion audits, and the exact `npm run build:web` command, then persists only a content-addressed command/artifact receipt in the outer tree.
- Evidence subset: Exact commands, tool versions, counts/durations, known pre-existing versus new failures, build/browser artifacts and digests
- Acceptance: Every required registry command is recorded with tool version, exit status and artifact digest; no new required failure remains; browser and build evidence is real; known baseline failures are distinguished exactly; excluded dependencies are absent; the receipt is bound to the exact source tree and three gitlinks and cannot claim checks not run; after receipt creation the outer tree differs only by that declared receipt.

## VGO-096 Publish architecture and application-extension guidance

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: architecture-docs
- Depends on: VGO-060, VGO-075, VGO-081, VGO-083, VGO-086
- Goal id: VGO-G110
- Outputs: swissknife/docs/gui-optimizer/ARCHITECTURE.md, external/ipfs_datasets/docs/gui_optimizer_contracts.md, external/ipfs_accelerate/docs/architecture/VERIFIED_GUI_OPTIMIZER.md, external/ipfs_accelerate/test/api/test_gui_optimizer_architecture_docs.py
- Validation: cd external/ipfs_accelerate && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:../ipfs_datasets python3 -m pytest test/api/test_gui_optimizer_architecture_docs.py -q && cd ../.. && PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_verified_gui_optimizer_board.py --check-all
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/architecture-docs
- Parallel lane: vgo-lane-1
- Resource class: docs
- Resource stage: documentation
- Implementation timeout seconds: 7200
- Predicted files: swissknife/docs/gui-optimizer/ARCHITECTURE.md, external/ipfs_datasets/docs/gui_optimizer_contracts.md, external/ipfs_accelerate/docs/architecture/VERIFIED_GUI_OPTIMIZER.md, external/ipfs_accelerate/test/api/test_gui_optimizer_architecture_docs.py
- Interfaces: VerifiedGuiOptimizerArchitecture@1, GuiApplicationAdapter@1, GuiEvidenceAuthorityMatrix@1
- Conflict policy: Document the implemented current tree and explicit extension seams; do not expand implementation to additional applications or claim aesthetic optimality/full WCAG/security proof. Commit and validate each affected nested repository first, then stage all exact gitlinks in one atomic superproject handoff with no dirty nested worktree.
- Preconditions: CLI, identity conformance, benchmark catalog and adversarial behavior are stable.
- Effects: Explains package boundaries, schemas, static/graph/state/formal/evaluation/invalidation/context/worktree loop, security model, evidence taxonomy, commands and exact adapter work for another screen; a cross-repository documentation test verifies required sections, current module/interface references, exclusions, evidence-level language and the narrow final claim.
- Evidence subset: Current modules/interfaces, formal/structural/heuristic/human matrix, diagrams tied to tests, extension checklist
- Acceptance: The documentation test and board validator pass; documentation states what is formally verified, structurally validated, heuristic and human-reviewed; records exclusions/non-goals without stale module references or overclaims; and lists exact manifest/target/scenario/action/test additions needed for another application.

## VGO-099 Emit the final current-tree improvement receipt and report

- Status: pending
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: closeout
- Depends on: VGO-090, VGO-091, VGO-093, VGO-096
- Goal id: VGO-G000
- Outputs: implementation_plan/evidence/verified_gui_optimizer/final-current-tree-receipt.json, implementation_plan/evidence/verified_gui_optimizer/final-report.md
- Validation: scripts/gui-opt report final-current-tree --require-complete --verify-receipts
- Board namespace: verified-gui-optimizer-v1
- Bundle: vgo/final-closeout
- Parallel lane: vgo-lane-0
- Resource class: cpu-small
- Resource stage: closeout
- Implementation timeout seconds: 7200
- Predicted files: implementation_plan/evidence/verified_gui_optimizer/final-current-tree-receipt.json, implementation_plan/evidence/verified_gui_optimizer/final-report.md
- Interfaces: GuiImprovementReceipt@1, VerifiedGuiOptimizerFinalReport@1
- Conflict policy: Report only exact current-tree evidence; never alter implementation, tests, benchmark outcomes, prior receipts or objective authority to manufacture completion. Closeout may add only its two declared files and the later status-only control transition; it must not make a self-referential claim that those bytes were present in the already verified source revision.
- Preconditions: Benchmark and security receipts are complete and individually bound to their evaluated revisions; architecture documentation is integrated; VGO-093 has freshly revalidated the final source tree and exact three gitlinks without mutating it.
- Effects: Rehashes every subordinate receipt and aggregates selected target/evaluated-source identity, modules, graph/state statistics, invariants, problems, accepted/rejected improvements, accessibility/interaction/visual/context/invalidation/route metrics, commands, limitations and extension prerequisites. The evaluated-source identity excludes the two closeout outputs and later status-only control commit, whose superproject commit identity is recorded separately after atomic handoff.
- Evidence subset: Rehashed subordinate receipts, exact gitlinks/revision, command ledger, acceptance/rejection reasons, unresolved limitation inventory
- Acceptance: Fail-closed reporting verifies every subordinate receipt, exact source-tree/gitlink identity and complete command ledger; the final receipt is closed, content-addressed and complete without a circular commit assertion; every visual/semantic claim carries its evidence level; actual unmet targets and failures remain visible; the source tree is unchanged since VGO-093; and the final claim is only that the selected workflow was incrementally analyzed and improved against declared criteria with content-addressed evidence.
