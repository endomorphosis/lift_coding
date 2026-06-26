# VAI-517 MCP Dashboard Launch Readiness Evidence

Task: VAI-517
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Track: launch

The objective gap receipt at
`data/virtual_ai_os/discovery/2026-06-26-vai-517-objective-gap-3e00ad2a0074.md`
called out the missing `launch Playwright validation gate` evidence for the
Hallucinate App MCP dashboard capability catalog. The launch gate is now bound
to a concrete Playwright receipt:

- Receipt fixture: `hallucinate_app/test/e2e/fixtures/vai-517-mcp-dashboard-launch-readiness.json`
- Catalog source: `hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog`
- Catalog schema: `hallucinate_app.mcp_dashboard_capability_catalog.v1`
- Backends: `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`
- Dashboard operations: `tools/list`, `tools/call`
- Packet sibling covered: VAIOS-G728
- Swissknife consumer: `hallucinate_app.swissknife.mcp_capability_registry`

The headless Playwright gate in
`hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
VAI-517 fixture against the live Hallucinate App daemon manager catalog. It
checks the launch packet ids, required backend packages, daemon health paths,
`tools/list`, `tools/call`, Swissknife consumer refs, and the shared
`launch Playwright validation gate` evidence term.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
