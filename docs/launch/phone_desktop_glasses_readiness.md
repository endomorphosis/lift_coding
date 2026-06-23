# Phone, Desktop, and Meta Glasses Launch Readiness

This readiness gate is the production-launch evidence for VAIOS-G697. It keeps
the phone-hosted Swissknife virtual desktop, desktop-peer offload, Hallucinate
App mediation, and Meta glasses terminal path open until a launch readiness
receipt proves each product-critical hop with deterministic Playwright coverage.

## Gate Contract

- Receipt schema: `launch_readiness_receipt_v1`
- Gate class term: `LaunchReadinessGate`
- Receipt packet: `data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md`
- HAO backlog packet: `data/hallucinate_multimodal_control/discovery/2026-06-23-hao-436-launch-readiness-gate.md`
- Physical phone ingress receipt: `data/hallucinate_multimodal_control/discovery/2026-06-23-hao-437-phone-ingress-rehearsal.md`
- Desktop-peer smoke receipt: `data/hallucinate_multimodal_control/discovery/2026-06-23-hao-438-desktop-peer-offload-smoke.md`
- Meta glasses terminal receipt: `data/hallucinate_multimodal_control/discovery/2026-06-23-hao-439-meta-glasses-terminal-receipt.md`
- MGW supervisor packet: `data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-274-launch-readiness-gate.md`
- Backlog bridge: `HAO-436` / `MGW-274` / `VAI-340` for `VAIOS-G697`
- Replay base: `data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md`
- Python guard: `tests/test_virtual_ai_os_launch_readiness_gate.py`
- Swissknife Playwright command: `npm --prefix swissknife run test:e2e:meta-glasses`
- Hallucinate App Playwright command: `npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts`

## Product-Critical Hops

| Hop | Launch evidence |
| --- | --- |
| Phone-originated command | HAO-437 adds the real phone ingress rehearsal receipt: a physical `phone:operator` UI event enters Hallucinate App as an `interaction_envelope`, preserves `session_id`, `correlation_id`, and `request_id`, blocks `desktop:peer` and `phone_local` dispatch until `mediation_receipt` and `policy_receipt_id` exist, and records fail-closed recovery when the physical adapter is absent. |
| Hallucinate App mediation | `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` exercises voice, gesture, mouse, agent, and remote Meta glasses clients through `policy_decision` and `mediation_receipt`. |
| Swissknife virtual desktop | `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` opens every Swissknife desktop app and writes a reusable Meta glasses ORB template report. |
| Desktop-peer offload | HAO-438 adds a desktop-peer offload smoke receipt: a phone-originated command selects `desktop:peer`, records capability and runtime health, emits `peer_offload_policy_receipt`, then recovers to `phone_local` with the same session, command, policy, and placement IDs when the peer is unavailable. |
| Meta glasses terminal | HAO-439 adds the Meta glasses terminal receipt: `display_action` events and confirmations from `meta_glasses:terminal` map through the existing HAO-431 bridge into normalized Hallucinate App `terminal.activate_action` intents, render selected peer and recovery state, and fail closed when pairing or display evidence is stale. The Swissknife Playwright gate also renders the Meta glasses display-widget contract and checks interface, widget, and receipt CIDs. |

## VAI-339 Replay Chain

`data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md`
contains the replayable chain for the deterministic launch slice. Its
`receipt_chain` orders the phone event, Hallucinate App mediation, placement,
desktop-peer execution, Meta glasses render, phone-local recovery, and final
capability reconciliation receipts. Every receipt carries the same `session_id`,
`command_id`, `correlation_id`, and `request_id`, and each non-root receipt
names the prior receipt CID as its parent.

## Launch Playwright Validation Gate

This is the `launch Playwright validation gate` evidence term required by the
VAIOS-G697 objective scan.

The launch gate passes only when these commands pass in order:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q
npm --prefix swissknife run test:e2e:meta-glasses
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

The Python guard is intentionally fast and static. It verifies the exact
Playwright scripts, specs, config, runner, heap evidence, readiness doc, VAI-339
replay packet, and `launch_readiness_receipt_v1` packet before the heavier
browser tests run. That prevents scanner-only AST matches from satisfying the
production objective.

The `LaunchReadinessGate` remains open until the Python guard, Swissknife
Playwright replay, and Hallucinate App Playwright mediation command all pass for
the same receipt lineage. Only that all-pass result moves the gate state to
`launch_ready`.

## Desktop-Peer Offload Smoke

`HAO-438` supplies the desktop-peer offload smoke receipt required by the
VAIOS-G697 physical-readiness split:
`data/hallucinate_multimodal_control/discovery/2026-06-23-hao-438-desktop-peer-offload-smoke.md`.
The receipt starts from `phone:operator`, passes through mediation, captures
`desktop:peer` capability and runtime health receipts, emits
`peer_offload_policy_receipt`, and then records deterministic recovery to
`phone_local` when the peer reports unavailable before dispatch.

The `phone_local` fallback preserves the same `session_id`,
`command_intent_id`, `policy_receipt_id`, `command_receipt_id`, `placement_id`,
and `peer_offload_policy_receipt_id`. Desktop peers may report capability,
runtime health, and transport failure; they do not own policy, fallback, retry,
or cancellation decisions.

## Meta Glasses Terminal Receipt

`HAO-439` supplies the Meta glasses terminal receipt required by the
VAIOS-G697 physical-readiness split:
`data/hallucinate_multimodal_control/discovery/2026-06-23-hao-439-meta-glasses-terminal-receipt.md`.
The receipt captures a `display_action` plus terminal confirmation from
`meta_glasses:terminal`, preserves the action payload in
`raw_payload.display_action`, and routes it through the existing HAO-431
display-action bridge before Hallucinate App emits the normalized
`terminal.activate_action` intent.

The allowed path renders `selected_peer: "desktop:peer"` and
`recovery_state: "running_on_peer"` back to `meta_glasses:terminal`. The
stale-evidence path denies the action with `policy_receipt_id: null`,
`dispatch_allowed: false`, and `recovery_state: "fail_closed"` when pairing or
display evidence is stale, so no terminal action, desktop handoff, or widget
open dispatch can occur.

## Real Phone Ingress Rehearsal

`HAO-437` supplies the real phone ingress rehearsal receipt required by the
VAIOS-G697 physical-readiness split:
`data/hallucinate_multimodal_control/discovery/2026-06-23-hao-437-phone-ingress-rehearsal.md`.
The receipt starts from physical `phone:operator` input and records the adapter
receipt before Hallucinate App builds the `interaction_envelope`.

The same `session_id`, `correlation_id`, and `request_id` are preserved through
`mediation_receipt`, `policy_receipt_id`, and `virtual_desktop_command_intent`.
The dispatch gate explicitly blocks `desktop:peer` and `phone_local` until both
the mediation receipt and policy receipt exist. When the physical phone adapter
is absent, the recovery receipt is `fail_closed`, has no `policy_receipt_id`,
sets `dispatch_allowed: false`, and records that no local or desktop runtime
dispatch occurred.

## Split Policy

No child goal is needed for this deterministic launch gate. Split VAIOS-G697
only if physical phone, physical desktop peer, or physical Meta glasses capture
fails independently after the Playwright launch gate is green.
