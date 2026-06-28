# VAI-530 Daemon Launch Health Gate

Task: VAI-530
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Track: launch

The objective gap receipt at
`data/virtual_ai_os/discovery/2026-06-27-vai-530-objective-gap-b023c8de5b69.md`
called out the missing `launch Playwright validation gate` evidence for
Hallucinate App daemon launch orchestration. The gap is now bound to the shared
daemon launch health gate:

- Receipt fixture: `hallucinate_app/test/e2e/fixtures/vai-530-daemon-launch-health-gate.json`
- Gate source: `hallucinate_app.node.mcp_daemon_manager.getDaemonLaunchValidationGate`
- Playwright spec: `hallucinate_app/test/e2e/daemon-launch-health.spec.ts`
- Gate owner: `MGW-535`
- Packet sibling covered: VAIOS-G724
- Backends: `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`
- Swissknife consumer handoff: `control_surface_contract:mcp-daemon:*`

The headless Playwright spec asserts the VAI-530 fixture against the live
Hallucinate App daemon manager gate. It checks the VAIOS-G724/VAIOS-G728 packet
ids, the `launch Playwright validation gate` evidence term, health and RPC paths
for every backend MCP daemon, required evidence terms, and the Swissknife
handoff records that downstream applications consume.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
