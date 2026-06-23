# VAI-012 Physical-Device and Desktop Operator Readiness

Date: 2026-06-23
Task: VAI-012
Track: device
Depends on: VAI-008, VAI-010, VAI-011

## Purpose

VAI-012 defines the readiness checklist and evidence plan for validating an
actual phone, desktop offload host, and Meta glasses session. This packet does
not claim that physical hardware has passed. It separates what the simulator
and hardware-free harness already prove from what must be manually verified on
devices.

## Inputs

- VAI-008 Meta glasses remote terminal contract:
  `data/virtual_ai_os/discovery/2026-06-23-vai-008-meta-glasses-remote-terminal.md`
- VAI-010 hardware-free end-to-end harness:
  `data/virtual_ai_os/discovery/2026-06-23-vai-010-hardware-free-e2e-harness.md`
- VAI-011 observability, policy, and rollback artifacts:
  `data/virtual_ai_os/discovery/2026-06-23-vai-011-observability-policy-rollback.md`
- VAI-017 simulator artifacts and Web App readiness:
  `data/virtual_ai_os/discovery/2026-06-23-vai-017-simulator-artifacts-mobile-orb-webapp-readiness.md`
- VAI-023 iPhone native DAT handoff:
  `data/virtual_ai_os/discovery/2026-06-12-vai-023-iphone-native-dat-handoff.md`

## Readiness Checklist

| Surface | Required before run | Evidence to collect |
| --- | --- | --- |
| Actual phone | Physical device available, OS version recorded, app build identifier recorded, backend URL/auth mode known, mobile ORB diagnostics baseline captured, native DAT/Web App/mobile-card flags recorded, Meta AI app installed, and pairing state captured before command issue. | Device model, OS version, app build, feature flags, backend URL/auth mode, `/v1/mobile/orb/diagnostics` snapshot, pairing/connectivity note or screenshot, redacted mobile logs. |
| Desktop operator host | Desktop host reachable from the phone path, repo/worktree pin recorded, Hallucinate App console available, SwissKnife ORB route available, desktop-peer placement policy known, and fallback behavior understood for disabled or disconnected offload. | Host/operator label, commit or worktree pin, console route note, SwissKnife route note, placement policy, network reachability result, remote execution receipt, disconnect/fallback receipt. |
| Meta glasses session | Glasses firmware/app state recorded, paired and unpaired behavior tested, audio command capture source known, spoken response target known, Web App HTTPS URL or native DAT display state recorded, D-pad/focus behavior checked, and pairing-loss recovery action visible. | Firmware/app versions, Meta AI app Web App URL or native DAT state, audio input/output note, display screenshot or operator note, D-pad/focus result, pairing-loss recovery receipt, fallback render target. |
| Shared session evidence | One run uses stable join keys across phone, desktop, and glasses surfaces. | `task_id`, `correlation_id`, `request_id`, `widget_id`, `widget_cid`, `descriptor_cid` or `interface_cid`, `policy_cid`, `receipt_cid`, parent receipt CIDs, placement change artifact, rollback artifact if used. |

## Evidence Plan

1. Start with simulator proof. Export or identify the VAI-017 simulator/Web App
   readiness bundle, including the 600x600 render metadata, focus order,
   command envelope, widget refs, ORB receipts, and fallback render targets.
2. Run or reference the VAI-010 hardware-free harness evidence for command
   routing, SwissKnife ORB binding, Hallucinate App operator routing,
   desktop-peer offload, streaming dispatch, and recovery.
3. Confirm VAI-011 reconciliation is available before hardware is attached:
   policy decisions, placement changes, remote execution receipts, validation
   failures, and rollback events must be joinable by `task_id`,
   `correlation_id`, and `artifact_id`.
4. Prepare the actual phone by recording device/build/backend state and taking
   a mobile ORB diagnostics baseline before the command is issued.
5. Prepare the desktop operator host by recording host identity, repo/worktree
   pin, Hallucinate App and SwissKnife availability, placement policy, and
   phone-to-host reachability.
6. Prepare the Meta glasses session by recording firmware/app state, pairing
   state, Web App HTTPS or native DAT display state, audio route state, and
   fallback render target.
7. Run one end-to-end physical session. The same command must produce phone
   diagnostics, desktop operator/offload receipts, and glasses-visible status
   that share the simulator-proven correlation, request, widget, policy, and
   receipt keys.
8. Trigger one recovery condition, preferably desktop offload disconnect or
   glasses pairing loss, and preserve the rollback/fallback artifact plus the
   visible operator or device status.
9. Redact private prompt content from committed logs, screenshots, and metrics
   while keeping enough IDs and status fields for reconciliation.

## Simulator-Only Coverage

The following remain simulator-only until manually verified on devices:

- Browser and harness proof of the constrained VAI-008 remote terminal route.
- Command routing through mobile ORB registration, event publication, service
  binding, invocation, and dispatch.
- 600x600 Web App rendering metadata, focus order, static package inventory,
  and public HTTPS readiness metadata.
- SwissKnife ORB and Hallucinate App operator flow in the hardware-free VAI-010
  harness.
- VAI-011 artifact shape, deterministic reconcile keys, retry-from rollback
  behavior, and policy/placement/receipt ordering.

## Manual Device Verification Required

These items must be verified on the actual phone, desktop host, and Meta
glasses before a physical-device readiness claim is valid:

- The phone can reach the configured backend and desktop operator host over the
  intended network with the selected auth mode.
- The Meta AI app can load the registered public HTTPS Web App URL, or the
  native DAT display path reports a valid display state with structured
  fallback when unavailable.
- The glasses can pair, lose pairing, and recover without ending the
  mobile-hosted session.
- Audio command capture and spoken response playback use the expected glasses
  or phone fallback endpoints.
- D-pad focus and activation match the simulator focus order on the actual
  glasses display surface or documented fallback surface.
- Desktop offload can be selected, observed by the desktop operator, and
  recovered to phone-local execution when disabled or disconnected.
- Phone diagnostics, desktop receipts, glasses-visible status, and rollback
  events reconcile to the same session keys without exposing private prompt
  content.

## Validation

Backlog validation command:

```bash
rg -n "VAI-012|physical-device|desktop operator|readiness" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
