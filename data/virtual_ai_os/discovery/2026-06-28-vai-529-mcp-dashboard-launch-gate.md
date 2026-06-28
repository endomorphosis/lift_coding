# VAI-529 MCP Dashboard Launch Gate Evidence

Task: VAI-529
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Track: launch

The objective gap receipt at
`data/virtual_ai_os/discovery/2026-06-27-vai-529-objective-gap-3e00ad2a0074.md`
called out the missing `launch Playwright validation gate` evidence for the
Hallucinate App MCP dashboard capability catalog. The VAI-owned gate is now
bound to a concrete receipt fixture and the live Hallucinate App dashboard
catalog:

- Receipt fixture: `hallucinate_app/test/e2e/fixtures/vai-529-mcp-dashboard-launch-gate.json`
- Catalog source: `hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog`
- Catalog schema: `hallucinate_app.mcp_dashboard_capability_catalog.v1`
- Backends: `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`
- Dashboard operations: `tools/list`, `tools/call`
- Daemon health paths: `/api/mcp/status`, `/health/ready`
- Packet sibling covered: VAIOS-G728
- Swissknife consumer: `hallucinate_app.swissknife.mcp_capability_registry`

Required evidence terms covered by this gate:

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

The Playwright gate in
`hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
VAI-529 fixture against the live `MCPDaemonManager` dashboard capability
catalog. It verifies the launch packet ids, required backend packages, daemon
health paths, `tools/list`, `tools/call`, safe-probe receipts, Swissknife
consumer refs, and the shared `launch Playwright validation gate` evidence
term.

`hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` also checks that the
dashboard catalog exposes the VAI-529 launch gate in `launch_validation_gates`
without changing the primary MGW-533 launch gate or introducing a duplicate
catalog schema.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
