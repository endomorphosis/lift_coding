# VAI-338 Launch Alignment Map Across VAI, MGW, and HAO

Date: 2026-06-23
Task: VAI-338
Track: launch
Depends on: none

## Purpose

This packet defines the launch alignment map for one ordered validation slice
across Virtual AI OS, Meta glasses display widgets (MGW), and Hallucinate App
operator mediation (HAO). The slice ties the VAI capability registry, MGW
display-widget contract, HAO mediation receipts, phone-hosted session model,
Swissknife operator surface, and desktop-peer offload path into one evidence
chain.

The map is intentionally narrower than full submodule hygiene. It identifies
what must pass for launch, what is simulator-only today, what requires physical
devices, what is not launch-critical, and what should be deferred to
non-launch submodule cleanup.

## Ordered Validation Slice

| Order | Validation step | Cross-project link | Evidence key | Classification |
| --- | --- | --- | --- | --- |
| 1 | Start a phone-hosted session with the canonical command envelope. | Phone host to VAI runtime. | `command_id`, `session_id`, `correlation_id`, `request_id`, backend/auth mode, mobile ORB diagnostics baseline. | Launch-critical. Simulator-only until VAI-012 physical phone evidence exists. |
| 2 | Resolve the command through the VAI capability registry. | VAI registry to MGW widget actions and Swissknife/HAO consumers. | `capability_id`, `descriptor_cid`, `manifest_cid`, `capability_receipt_cid`, policy receipt, placement receipt. | Launch-critical. CI-safe simulator validation. |
| 3 | Mediate the command through Hallucinate App. | HAO operator console to VAI observability artifacts. | `interaction_envelope`, `normalized_intent`, `policy_decision`, `mediation_receipt`, `virtual_desktop_command_intent`. | Launch-critical. Simulator-only unless a desktop operator host is attached. |
| 4 | Present the virtual desktop state through Swissknife. | Swissknife ORB to MGW display descriptor and HAO operator visibility. | ORB service binding, widget ID/CID, descriptor CID, stream receipt, desktop fallback panel state. | Launch-critical. Simulator-only in default replay. |
| 5 | Execute locally or offload to a desktop peer. | VAI placement policy to desktop-peer runtime and HAO recovery view. | `placement_change`, remote execution receipt, peer stream receipt, fallback-to-phone rollback event. | Launch-critical for evidence shape. Physical-device-gated for real desktop-peer reachability. |
| 6 | Render the terminal state to Meta glasses or fallback display. | MGW display-widget contract to phone-hosted Meta glasses terminal. | `vai.glasses_widget.render`, `vai.glasses_widget.update`, `vai.glasses_widget.confirm`, `vai.glasses_widget.cancel`, fallback render target, glasses-visible status note. | Launch-critical for contract validation. Physical-device-gated for real Meta glasses. |
| 7 | Reconcile recovery without losing the phone session. | Phone, desktop peer, Hallucinate App, Swissknife, and Meta glasses receipts. | Validation failure, rollback event, degraded edge reason, parent receipt CIDs, recovered placement. | Launch-critical. Simulator-only for CI and physical-device-gated for final rehearsal. |
| 8 | Keep unrelated cleanup outside the launch gate. | VAI, MGW, HAO backlog hygiene. | Pin notes, codebase scans, duplicate backlog cleanup, nonblocking source hygiene tasks. | Not launch-critical; deferred to non-launch submodule hygiene. |

## Required Join Contract

The launch replay must preserve the same join keys across the phone,
Hallucinate App, Swissknife, desktop peer, and Meta glasses paths:

- `task_id`
- `command_id`
- `session_id`
- `correlation_id`
- `request_id`
- `widget_id`
- `widget_cid`
- `descriptor_cid` or `interface_cid`
- `manifest_cid`
- `policy_cid`
- `capability_receipt_cid`
- parent receipt CIDs for mediation, placement, render, remote execution, and
  rollback artifacts

Missing join keys are launch blockers. Unavailable physical surfaces are not
implementation failures when the simulator, fallback render path, degraded edge
reason, and parent receipt lineage remain intact.

## Launch-Critical

- Phone-hosted session control and mobile ORB diagnostics.
- VAI capability registry resolution for the MGW widget render, update,
  confirm, and cancel actions in this launch alignment map.
- HAO mediation receipts and policy decisions that reconcile with VAI
  observability artifacts.
- Swissknife ORB route visibility and virtual desktop state for the same
  command.
- Desktop-peer offload evidence shape, including fallback to phone-local
  placement.
- MGW render/update/confirm/cancel receipts for Meta glasses terminal status
  and Web App or mobile-card fallback.
- Recovery evidence for offload disconnect, Meta glasses pairing loss, or
  native DAT absence.

## Simulator-Only Until Rehearsal

- Capability routing, registry lookup, HAO mediation shape, Swissknife ORB
  binding, MGW display-widget rendering, and rollback artifact ordering.
- Meta glasses Web App or mobile-card fallback render metadata when no physical
  glasses are paired.
- Desktop-peer offload behavior in the deterministic hardware-free harness
  when no real peer is reachable.

## Physical-Device-Gated

- Actual phone network reachability to backend and desktop operator host.
- Meta AI app Web App loading or native DAT display state on real Meta glasses.
- Glasses pairing, pairing loss, audio capture/playback route, D-pad/focus, and
  visible recovery action.
- Real desktop-peer offload reachability, disconnect recovery, and operator
  visibility from Hallucinate App and Swissknife.

## Not Launch-Critical

- Broad codebase scans that do not affect the ordered replay slice.
- Cosmetic documentation cleanup unrelated to VAI, MGW, HAO, phone, desktop
  peer, Swissknife, Hallucinate App, or Meta glasses validation.
- Optional native DAT refinements when Web App or mobile-card fallback preserves
  the same receipt lineage.

## Deferred To Non-Launch Submodule Hygiene

- Source pin refreshes that do not change the launch replay contract.
- Duplicate backlog cleanup, stale retry-budget housekeeping, and broad
  submodule metadata normalization.
- Future MCP/MCP++ service expansion outside the current phone-hosted virtual
  desktop and display-widget contract.

## Dependency Handoff

- VAI-009 supplies the component repository and root override contract.
- VAI-012 defines what must move from simulator proof into the physical phone,
  desktop peer, and Meta glasses rehearsal.
- VAI-024 supplies the Hallucinate App and Swissknife desktop operator evidence
  path.
- This map is dependency-free in backlog metadata; prior VAI evidence packets
  remain useful references but are not blocking prerequisites for VAI-338.

## Validation

Backlog validation command:

```bash
rg -n "VAI-338|launch alignment|phone|desktop peer|Meta glasses|Hallucinate App|Swissknife" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
