# MGW-565 Daemon Launch Health Gate

- Task: MGW-565
- Goal: VAIOS-G728
- Packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Packet goals: VAIOS-G724, VAIOS-G728
- Missing evidence closed: launch Playwright validation gate
- Source gap: data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-objective-gap-b023c8de5b69.md
- Gate fixture: hallucinate_app/test/e2e/fixtures/mgw-565-daemon-launch-health-gate.json
- Playwright gate: hallucinate_app/test/e2e/daemon-launch-health.spec.ts
- Swissknife consumer gate: swissknife/test/e2e/meta-glasses-virtual-os.spec.ts
- Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md

## Evidence

MGW-565 now has a first-class Hallucinate App daemon launch validation gate in
`MCPDaemonManager.getDaemonLaunchValidationGates()`. The gate is tied to the
same launch packet as MGW-535, keeps the supervisor-fed backlog aligned with
VAIOS-G724 and VAIOS-G728, and remains open until the Playwright validation
commands pass.

The daemon launch contract covers the `hallucinate_app` launcher, `swissknife`
consumer handoff, and backend daemon surfaces from `external/ipfs_kit`,
`external/ipfs_datasets`, and `external/ipfs_accelerate`. Required runtime
packages remain `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.

Required evidence terms covered by this gate: Hallucinate App daemon health,
daemon launcher, MCP server, MCP dashboard, ipfs_accelerate_py,
ipfs_datasets_py, ipfs_kit_py, dashboard capability catalog, Swissknife applications,
and launch Playwright validation gate.

## Validation Commands

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Gate Fixture

```json
{
  "schema": "hallucinate_app.daemon_launch_validation_gate.v1",
  "task_id": "MGW-565",
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "gate_state": "gate_open_until_playwright_passes",
  "discovery_receipts": [
    "data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-daemon-launch-health-gate.md"
  ],
  "objective_gap_receipt": "data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-objective-gap-b023c8de5b69.md",
  "objective_gap_receipts": [
    "data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-objective-gap-b023c8de5b69.md"
  ],
  "supervisor_gap_receipt": "data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-objective-gap-b023c8de5b69.md",
  "launch_gate_receipt": "data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-daemon-launch-health-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/mgw-565-daemon-launch-health-gate.json",
  "validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "playwright_specs": [
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ]
}
```

## Gate Rule

Any daemon launch, health, dashboard catalog, Swissknife handoff, or Playwright
validation failure remains supervisor-generated follow-up work for VAIOS-G728.
