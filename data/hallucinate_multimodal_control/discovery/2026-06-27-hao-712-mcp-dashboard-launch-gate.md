# HAO-712 MCP Dashboard Launch Gate

Date: 2026-06-27
Task: HAO-712
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-27-hao-712-objective-gap-3e00ad2a0074.md

## Gate

HAO-712 closes the Hallucinate App objective scan gap for `VAIOS-G724` by tying
the current dashboard capability catalog to the launch Playwright validation
gate consumed by the supervisor-fed backlog.

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
  `launch_validation_gates` catalog entry for `HAO-712`, `VAIOS-G724`, packet
  sibling `VAIOS-G728`, the source gap receipt, this launch gate receipt, and
  the two Hallucinate App Playwright specs.
- `hallucinate_app/test/e2e/fixtures/hao-712-mcp-dashboard-launch-gate.json`
  records the HAO-712 receipt for the dashboard capability catalog and packet
  sibling launch checks.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  fixture, this discovery receipt, the objective gap receipt, the objective
  heap proof, the shared `MCPDaemonManager` dashboard capability catalog,
  `tools/list`, `tools/call`, daemon health paths, and Swissknife consumer refs.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` asserts the same
  HAO-712 catalog gate from the Hallucinate App Electron surface and the
  headless Playwright path.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  the HAO-712 proof under `VAIOS-G724` while preserving packet sibling
  `VAIOS-G728`.

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
operation, Swissknife handoff, or Playwright proof remains supervisor-fed launch
work for `VAIOS-G724` and `VAIOS-G728`.
