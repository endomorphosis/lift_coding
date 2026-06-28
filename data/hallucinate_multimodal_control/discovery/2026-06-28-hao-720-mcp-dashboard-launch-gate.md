# HAO-720 MCP Dashboard Launch Gate

Date: 2026-06-28
Task: HAO-720
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-28-hao-720-objective-gap-3e00ad2a0074.md

## Gate

HAO-720 closes the Hallucinate App objective scan gap for `VAIOS-G724` by
binding the MCP dashboard capability catalog to the launch Playwright
validation gate consumed by the supervisor-fed backlog and the Swissknife
dashboard catalog consumer.

The focused dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full launch packet command remains:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes a
  `launch_validation_gates` catalog entry for `HAO-720`, `VAIOS-G724`, packet
  sibling `VAIOS-G728`, the source gap receipt, this launch gate receipt, and
  the Hallucinate App dashboard Playwright specs.
- `hallucinate_app/test/e2e/fixtures/hao-720-mcp-dashboard-launch-gate.json`
  records the HAO-720 receipt for the dashboard capability catalog, daemon
  health paths, `tools/list`, `tools/call`, and packet sibling launch checks.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  fixture, this discovery receipt, the objective heap proof, the shared
  `MCPDaemonManager` dashboard capability catalog, Swissknife consumer refs,
  and the three IPFS MCP package dashboards.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` asserts the same
  HAO-720 catalog gate from the Hallucinate App Electron surface and the
  headless Playwright path.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` checks that the
  Swissknife catalog consumer sees the same HAO-720 gate from the shared
  Hallucinate App dashboard capability catalog.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  the HAO-720 proof under `VAIOS-G724` and packet sibling `VAIOS-G728`.

## Covered Terms

- hallucinate_app menus
- Hallucinate App MCP dashboard
- dashboard capability catalog
- daemon health
- tools/list
- tools/call
- ipfs_accelerate_py MCP server
- ipfs_datasets_py MCP server
- ipfs_kit_py MCP server
- Swissknife applications
- Playwright MCP dashboard interoperability
- launch Playwright validation gate

## Gate State

The gate remains open until the launch runner passes the focused dashboard gate
and the full packet command. Any missing catalog, daemon health, MCP tool
operation, Swissknife handoff, or Playwright proof remains supervisor-fed
launch work for `VAIOS-G724` and `VAIOS-G728`.
