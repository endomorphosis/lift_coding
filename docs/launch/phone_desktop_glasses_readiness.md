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
- MGW supervisor packet: `data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-274-launch-readiness-gate.md`
- Backlog bridge: `HAO-436` / `MGW-274` / `VAI-340` for `VAIOS-G697`
- Replay base: `data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md`
- Python guard: `tests/test_virtual_ai_os_launch_readiness_gate.py`
- Swissknife Playwright command: `npm --prefix swissknife run test:e2e:meta-glasses`
- Hallucinate App Playwright command: `npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts`

## Product-Critical Hops

| Hop | Launch evidence |
| --- | --- |
| Phone-originated command | VAI-339 replay keeps the shared capability envelope, request id, command id, session id, and receipt lineage in one evidence packet. |
| Hallucinate App mediation | `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` exercises voice, gesture, mouse, agent, and remote Meta glasses clients through `policy_decision` and `mediation_receipt`. |
| Swissknife virtual desktop | `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` opens every Swissknife desktop app and writes a reusable Meta glasses ORB template report. |
| Desktop-peer offload | The VAI-339 launch replay receipt keeps `desktop_peer` placement with `phone_local` recovery in the parent lineage. |
| Meta glasses terminal | The Swissknife Playwright gate renders the Meta glasses display-widget contract and checks interface, widget, and receipt CIDs. |

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

## Split Policy

No child goal is needed for this deterministic launch gate. Split VAIOS-G697
only if physical phone, physical desktop peer, or physical Meta glasses capture
fails independently after the Playwright launch gate is green.
