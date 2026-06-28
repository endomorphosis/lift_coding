# MGW-555 Launch Playwright Validation Gate

Date: 2026-06-28
Task: MGW-555
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-555-objective-gap-3e00ad2a0074.md

## Gate

MGW-555 keeps the Meta glasses dashboard objective scan aligned with the
shared Hallucinate App MCP dashboard capability catalog gate consumed by
Swissknife and Virtual AI OS.

The focused dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full launch packet command remains:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

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

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the
  `MGW-555` launch gate in the shared dashboard capability catalog.
- `hallucinate_app/test/e2e/fixtures/mgw-555-mcp-dashboard-launch-gate.json`
  records the matching launch readiness receipt for `VAIOS-G724` and packet
  sibling `VAIOS-G728`.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`,
  `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`, and
  `swissknife/scripts/test-mcp-dashboard-consumer.cjs` assert the gate against
  the live catalog, `tools/list`, `tools/call`, daemon health paths, and the
  three IPFS MCP package dashboards.

## Gate State

Any missing catalog entry, daemon health route, MCP tool operation, Swissknife
handoff, or Playwright proof remains launch work for `VAIOS-G724` and packet
sibling `VAIOS-G728`.
