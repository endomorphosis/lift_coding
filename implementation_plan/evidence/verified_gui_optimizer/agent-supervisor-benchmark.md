# Agent Supervisor controlled benchmark (VGO-090)

- Benchmark: `benchmark-v1` / `catalog:gui-optimizer-benchmark-v1`
- Run: `run:vgo-090-benchmark-v1`
- Repository revision: `dda22aace054b1df19de2498b2adbd80b84f3a67`
- Expected tasks: 15
- Terminal receipts: 15
- Verification: `integrity_valid`
- Receipt: `receipt:vgo-090-benchmark-v1`

## Fail-closed summary

This report evaluates the current Agent Supervisor tree against the sealed 15-task `benchmark-v1` catalog. Canonical source was not modified by this run. VGO-080 already admitted the focus-restore and error-association patch; remaining catalog objectives are reported from the archived VGO-068 live baseline plus current source observation. Unmet targets stay visible.

Zero critical accessibility regressions and zero authorization/confirmation regressions were automatically accepted.

## Target attainment

- Median context reduction: **0.00%** (target ≥ 30%): **NOT MET**
- Invalidation precision: **100.00%** (target 100% unrelated-screenshot exclusion): met
- Automatically accepted critical accessibility regressions: **0** (target 0): met
- Automatically accepted authorization/confirmation regressions: **0** (target 0): met
- Accepted tasks with measurable objective improvement: **True**

The 30% median context-reduction target is disclosed as unmet. `UiContextPack@1` requires editable target source to remain raw. The current `swissknife/web/js/apps/agent-supervisor.js` is 2086 lines, so a pack that includes that required raw source exceeds the sealed catalog ordinary-retrieval estimates (1580–1900 tokens) and cannot claim a 30% reduction.

## Decision distribution

- `accept`: 2
- `human_review`: 1
- `pending`: 0
- `reject`: 12

## Route / method distribution

- `deterministic_transform`: 14
- `human_review`: 1

## Method distribution

- `aria_reference_repair`: 3
- `design_token_substitution`: 2
- `exact_action_binding_migration`: 3
- `exact_aria_reference_repair`: 1
- `exact_label_substitution`: 3
- `exact_route_migration`: 2
- `human_hierarchy_review`: 1

## Task receipts

| Task | Kind | Decision | Route | Metric before → after | Context reduction | Invalidation precision | Receipt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `task:focus-restoration` | `focus_restoration` | `accept` | `deterministic_transform` | 0.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:focus-restoration` |
| `task:accessible-labels` | `accessible_labels` | `reject` | `deterministic_transform` | 0.3279 → 0.3279 | 0.00% | 100.00% | `receipt:vgo-090:accessible-labels` |
| `task:error-presentation` | `error_presentation` | `accept` | `deterministic_transform` | 0.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:error-presentation` |
| `task:loading-state` | `loading_state` | `reject` | `deterministic_transform` | 1.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:loading-state` |
| `task:failure-state` | `failure_state` | `reject` | `deterministic_transform` | 1.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:failure-state` |
| `task:interaction-step-reduction` | `interaction_step_reduction` | `reject` | `deterministic_transform` | 17 → 17 | 0.00% | 100.00% | `receipt:vgo-090:interaction-step-reduction` |
| `task:responsive-overflow` | `responsive_overflow` | `reject` | `deterministic_transform` | 47 → 47 | 0.00% | 100.00% | `receipt:vgo-090:responsive-overflow` |
| `task:primary-action-hierarchy` | `primary_action_hierarchy` | `human_review` | `human_review` | 0.5 → 0.5 | 0.00% | 100.00% | `receipt:vgo-090:primary-action-hierarchy` |
| `task:design-token-consistency` | `design_token_consistency` | `reject` | `deterministic_transform` | 0.0 → 0.0 | 0.00% | 100.00% | `receipt:vgo-090:design-token-consistency` |
| `task:confirmation-ux` | `confirmation_ux` | `reject` | `deterministic_transform` | 0.5 → 0.5 | 0.00% | 100.00% | `receipt:vgo-090:confirmation-ux` |
| `task:empty-state-guidance` | `empty_state_guidance` | `reject` | `deterministic_transform` | 1.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:empty-state-guidance` |
| `task:keyboard-reachability` | `keyboard_reachability` | `reject` | `deterministic_transform` | 0.35 → 0.35 | 0.00% | 100.00% | `receipt:vgo-090:keyboard-reachability` |
| `task:localization-clipping` | `localization_clipping` | `reject` | `deterministic_transform` | 0 → 0 | 0.00% | 100.00% | `receipt:vgo-090:localization-clipping` |
| `task:modal-focus-lifecycle` | `modal_focus_lifecycle` | `reject` | `deterministic_transform` | 0.0 → 0.0 | 0.00% | 100.00% | `receipt:vgo-090:modal-focus-lifecycle` |
| `task:action-binding-integrity` | `action_binding_integrity` | `reject` | `deterministic_transform` | 1.0 → 1.0 | 0.00% | 100.00% | `receipt:vgo-090:action-binding-integrity` |

## Failed or review-required cases

- `task:accessible-labels` (`accessible_labels`): `reject` — rejected, no_measurable_improvement. Archived live baseline still records unlabeled interactive controls. No accessible-name patch was admitted after VGO-080. Objective remains unmet.
- `task:loading-state` (`loading_state`): `reject` — rejected, no_measurable_improvement. Loading outcome already exists in both the archived live baseline (`missing_loading_error_behavior_count=0`) and the current tree. This run applied no new patch and recorded no metric delta.
- `task:failure-state` (`failure_state`): `reject` — rejected, no_measurable_improvement. Failure/recovery outcome already exists in the archived live baseline and current tree. This run applied no new patch and recorded no metric delta.
- `task:interaction-step-reduction` (`interaction_step_reduction`): `reject` — rejected, no_measurable_improvement. Archived live `interaction_step_count` remains 17. No step-reduction patch was admitted. Confirmation hard gate is unchanged.
- `task:responsive-overflow` (`responsive_overflow`): `reject` — rejected, no_measurable_improvement. Archived live baseline still records `horizontal_overflow_count=13` and `viewport_overflow_count=34`. Current source still has `min-width:1280px` gateway rows. Objective remains unmet.
- `task:primary-action-hierarchy` (`primary_action_hierarchy`): `human_review` — human_review_required, proposal_escalated. Primary-action hierarchy is a subjective task and cannot be automatically accepted.
- `task:design-token-consistency` (`design_token_consistency`): `reject` — rejected, no_measurable_improvement. Current source still uses hardcoded hex surfaces rather than a closed design-token substitution. No token patch was admitted.
- `task:confirmation-ux` (`confirmation_ux`): `reject` — rejected, no_measurable_improvement. Confirmation checkboxes and tokens are present, but the archived `confirmation_failure_count=1` (static confirmation is not argument-digest-bound) was not cleared by a new admitted patch.
- `task:empty-state-guidance` (`empty_state_guidance`): `reject` — rejected, no_measurable_improvement. Empty-state guidance already exists in the archived live baseline and current tree. This run applied no new patch and recorded no metric delta.
- `task:keyboard-reachability` (`keyboard_reachability`): `reject` — rejected, no_measurable_improvement. Archived live baseline still records keyboard-activation, keyboard-reachability, and keyboard-order defects on custom tree controls. No keyboard patch was admitted.
- `task:localization-clipping` (`localization_clipping`): `reject` — rejected, no_measurable_improvement. Archived live `clipping_count` is already 0. This run applied no new localization patch and recorded no metric delta.
- `task:modal-focus-lifecycle` (`modal_focus_lifecycle`): `reject` — rejected, no_measurable_improvement. Archived live baseline records a focus-trap problem. Current source has `restoreFocusState` but no modal focus trap. Objective remains unmet.
- `task:action-binding-integrity` (`action_binding_integrity`): `reject` — rejected, no_measurable_improvement. Archived live `action_binding_invalid_count` is already 0. This run applied no new binding patch and recorded no metric delta. Confirmation and host gates remain closed.

## Artifact manifest

- Manifest CID: `bafkreibswlqxejb5wlnnubaqmxd7b2pk5ivwnetoxuovt2wgeq3oka4eyq`
- Manifest digest: `sha256:ee909b29ca9ca7e3a5dbb66eddcccd5c0034c48d0364bb27531a64bf9055b7fb`
- Bound CIDs are the host-owned VGO-068 baseline CAS objects consumed as the live baseline, plus the VGO-080/081 improvement and regression receipts.
- Every listed CID is a verified CIDv1 from that host-owned inventory.

## Deterministic rerun

- Archived VGO-068 baseline identity is unchanged: `sha256:7172d7ef1587e57295670cd355a4b6feb577f0dc54919045ebdebf02d4c75553`
- VGO-081 records matching first/second accessibility and interaction identities for the target screen.

## Limitations

- This run did not apply new patches to the canonical branch. Only the previously admitted VGO-080 focus-restore and error-association improvement is treated as an accepted metric delta versus the archived VGO-068 live baseline.
- Median context reduction is reported fail-closed as 0.0. The unmet 30% target is disclosed rather than hidden.
- Remaining catalog defects were not live-rebrowsered in this run. Candidate metrics stay at the archived VGO-068 live snapshot unless VGO-080/081 source evidence proves the specific improvement.
- Primary-action hierarchy is forbidden from automatic acceptance.
