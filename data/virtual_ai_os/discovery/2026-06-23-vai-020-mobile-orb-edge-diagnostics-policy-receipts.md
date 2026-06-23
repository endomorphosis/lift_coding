# VAI-020 Mobile ORB Edge Diagnostics and Policy Receipts

Date: 2026-06-23
Task: VAI-020
Track: mobile

## Scope

VAI-020 records how mobile ORB edge diagnostics and policy receipts should be
used by the supervisor when a glasses-terminal command routes through the
mobile host. The goal is to distinguish implementation failure from unavailable
device conditions without searching transient mobile logs.

## Reviewed surfaces

| Surface | Evidence use |
| --- | --- |
| `src/handsfree/api.py` | `/v1/mobile/orb/diagnostics` aggregates edge sessions, bindings, subscriptions, events, invocations, dispatches, and revocations into `handsfree.meta-glasses/mobile-orb-diagnostics@0.1.0`. |
| `mobile/src/orb/metaGlassesMobileOrbBridge.js` | The mobile edge bridge records local diagnostics artifacts, receipt CIDs, policy CIDs, fallback reasons, and binding state for simulator or physical-device mode. |
| `src/handsfree/meta_glasses_mobile_orb_artifacts.py` | Backend artifact helpers normalize remote-client interactions into canonical control-surface envelopes, policy decisions, and mediation receipts. |
| `tests/test_meta_glasses_mobile_orb_bridge.py` | Proves policy receipt collection, receipt integrity, degraded edge health, missing policy CID detection, orphan parent receipt detection, fallback reasons, and binding/subscription state. |
| `tests/test_virtual_ai_os_end_to_end_harness.py` | Proves command routing, desktop offload, dispatch, fallback-to-phone recovery, and diagnostics receipt lineage in the hardware-free virtual AI OS harness. |

## Required diagnostic fields

The supervisor should persist or reconcile these fields from the diagnostics
payload:

- `backend_counts`: separates missing backend records from a live but empty
  edge condition.
- `binding_state`: records registered, bound, subscribed, or missing edge
  state plus active binding and subscription identifiers.
- `policy_receipts`: summarizes mediation receipt ID, decision ID, outcome,
  policy CID, method, and target reference for each routed command.
- `receipt_integrity`: reports total records, missing receipts, missing policy
  CID receipts, parent receipt orphans, and policy outcome counts.
- `edge_health`: classifies the edge as healthy, degraded, or unknown and
  carries degradation reasons.
- `receipt_cids`, `policy_cids`, and `descriptor_cids`: provide durable join
  keys across simulator, mobile ORB, backend, SwissKnife, and DAT handoff
  evidence.
- `fallback_reasons`: records unavailable-device conditions such as
  `dat_native_display_unavailable`, mobile-card fallback, phone-speaker
  fallback, or other display/audio fallback paths.

## Acceptance mapping

| Required case | Receipt and diagnostic requirement | Supervisor interpretation |
| --- | --- | --- |
| Command routing | Event, binding, invocation, and dispatch records must share `correlation_id`, parent receipt CIDs, descriptor CIDs, and allow outcomes in `policy_receipts`. | If receipts are intact, route execution is implemented; missing records or orphan parents indicate implementation or persistence failure. |
| Offload selection | The invoked service result and dispatch record must preserve placement/offload status, parent receipt CIDs, and render targets while `binding_state.status` remains `bound` or `subscribed`. | A desktop peer disconnect with fallback receipts is an unavailable peer condition; missing invoke or dispatch receipts are implementation failures. |
| Permission denial | Deny, require-confirmation, defer, or rate-limit outcomes must appear in `policy_receipts` and `receipt_integrity.outcomes`, with policy CID present unless the test is explicitly exercising missing policy metadata. | A denied command with a complete mediation receipt is policy behavior; a command without a policy receipt is a diagnostics or implementation failure. |
| Recovery | Recovery dispatches must add fallback reasons and parent links to the failed invocation or dispatch receipt, and `edge_health.degraded_reasons` must name the unavailable surface. | Fallback to phone, mobile card, Web App, or phone speaker is a device/surface availability condition when receipts are intact; absent recovery receipts are implementation failures. |

## Current decision

The mobile ORB diagnostics contract is the supervisor handoff for VAI-020. A
supervisor should not infer failure from a degraded edge alone. It should first
check whether `receipt_integrity` is complete and whether `edge_health` names a
known unavailable-device reason. Complete policy receipts plus a degraded reason
such as `dat_native_display_unavailable` mean the implementation routed and
recovered correctly, while missing receipts, missing policy CIDs, unknown edge
state, or orphan parent receipts require implementation remediation.

## Validation

Backlog validation command:

```bash
rg -n "VAI-020|ORB edge diagnostics|policy receipts" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
