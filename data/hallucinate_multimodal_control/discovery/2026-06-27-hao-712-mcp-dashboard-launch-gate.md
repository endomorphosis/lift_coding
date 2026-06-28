# HAO-712 MCP Dashboard Launch Gate

Date: 2026-06-27
Task: HAO-712
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

## Gate

HAO-712 binds the Hallucinate App MCP dashboard capability catalog to the
current VAIOS-G724 launch Playwright validation gate while preserving packet
sibling coverage for VAIOS-G728.

The focused dashboard command is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/test/e2e/fixtures/hao-712-mcp-dashboard-launch-gate.json`
  records the source gap receipt, packet goals, validation commands, and
  required evidence.
- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes HAO-712
  in the shared dashboard catalog beside the MGW launch gates.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  catalog, daemon health, `tools/list`, `tools/call`, Swissknife consumers, and
  this discovery receipt.

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
