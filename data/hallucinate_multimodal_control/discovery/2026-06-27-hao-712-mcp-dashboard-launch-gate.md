# HAO-712 MCP Dashboard Launch Gate

Date: 2026-06-27
Task: HAO-712
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-27-hao-712-objective-gap-3e00ad2a0074.md

HAO-712 closes the Hallucinate-owned objective scan gap for the MCP dashboard
capability catalog by binding VAIOS-G724 to the shared Hallucinate App
Playwright launch gate:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full launch packet command keeps the sibling VAIOS-G728 evidence in the same
gate:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

## Gate Fixture

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-712",
  "shared_packet_task_id": "MGW-533",
  "goal_id": "VAIOS-G724",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goal_ids": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "source_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-712-objective-gap-3e00ad2a0074.md",
  "evidence_term": "launch Playwright validation gate",
  "playwright_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "required_evidence": [
    "hallucinate_app menus",
    "Hallucinate App MCP dashboard",
    "dashboard capability catalog",
    "daemon health",
    "tools/list",
    "tools/call",
    "ipfs_accelerate_py MCP server",
    "ipfs_datasets_py MCP server",
    "ipfs_kit_py MCP server",
    "Swissknife applications",
    "Playwright MCP dashboard interoperability",
    "launch Playwright validation gate"
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G724",
    "packet_sibling_goal": "VAIOS-G728",
    "backlog_task": "HAO-712",
    "shared_packet_task": "MGW-533",
    "keeps_supervisor_fed_backlog_aligned": true
  }
}
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` keeps
  `MGW-533` as the shared packet gate and adds the HAO-712 Hallucinate backlog
  proof to `launch_validation_gate.hallucinate_backlog_proofs`.
- `hallucinate_app/test/e2e/fixtures/hao-712-mcp-dashboard-launch-gate.json`
  records the VAIOS-G724 launch receipt and packet sibling VAIOS-G728.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` asserts the catalog
  exposes the HAO-712 backlog proof beside the shared launch gate.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  HAO-712 fixture against the live `MCPDaemonManager` dashboard capability
  catalog, including `daemon health`, `tools/list`, `tools/call`,
  `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`, Swissknife
  consumers, and the launch Playwright validation gate.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-712 proof under VAIOS-G724 and references VAIOS-G728 to keep the
  supervisor-fed backlog aligned with the objective heap.

## Gate State

The gate remains open until the validation command passes in the launch runner.
Any missing catalog, daemon health, MCP tool operation, Swissknife handoff, or
Playwright proof remains supervisor-fed launch work for VAIOS-G724 and
VAIOS-G728.
