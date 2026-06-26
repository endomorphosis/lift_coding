# VAI-519 Daemon Launch Health Gate Evidence

Task: VAI-519
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Track: launch

The objective gap receipt at
`data/virtual_ai_os/discovery/2026-06-26-vai-519-objective-gap-b023c8de5b69.md`
called out the missing `launch Playwright validation gate` evidence for the
Hallucinate App daemon launch orchestration goal. The VAI-owned launch receipt
now binds that gap to the same daemon health gate exposed by
`hallucinate_app.node.mcp_daemon_manager.getDaemonLaunchValidationGate`.

- Receipt fixture: `hallucinate_app/test/e2e/fixtures/vai-519-daemon-launch-health-gate.json`
- Playwright spec: `hallucinate_app/test/e2e/daemon-launch-health.spec.ts`
- Backends: `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`
- Daemon proof: Hallucinate App daemon health, daemon launcher, MCP server, MCP dashboard
- Packet sibling covered: VAIOS-G724
- Swissknife applications: every daemon launch plan entry names its Swissknife consumer and mediation contract ref

The Playwright gate compares the VAI-519 fixture against the live Hallucinate App
daemon manager. It checks the launch packet ids, required backend packages,
daemon health paths, MCP RPC paths, dashboard evidence terms, Swissknife handoff
records, and the shared `launch Playwright validation gate` evidence term.

## Gate Fixture

```json
{
  "schema": "virtual_ai_os.daemon_launch_validation_gate.v1",
  "task_id": "VAI-519",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "playwright_specs": [
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "npm --prefix swissknife run test:e2e:meta-glasses",
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ]
}
```

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
