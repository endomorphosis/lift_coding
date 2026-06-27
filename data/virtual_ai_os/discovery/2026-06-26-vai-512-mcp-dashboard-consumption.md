# VAI-512 MCP Dashboard Consumption Evidence

Task: VAI-512
Goal id: VAIOS-G723
Track: validation

Hardware-free Playwright and Swissknife validation now share one Hallucinate App
dashboard capability catalog fixture:

- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json`
- `hallucinate_app/test/e2e/fixtures/vai-512-hallucinate-swissknife-mcp-dashboard-consumption.json`
- Catalog schema: `hallucinate_app.mcp_dashboard_capability_catalog.v1`
- Catalog source: `hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog`
- Backends: `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`
- Mediated operations: `tools/list`, `tools/call`
- Shared receipt schema: `mcp_server_invocation_receipt_v1`

The Hallucinate Playwright gate verifies that the fixture matches the live
daemon manager catalog shape and then runs the Swissknife consumer validator
against the same fixture. Swissknife asserts that all three backend packages
consume the catalog without duplicate catalog schemas and with
`dashboard_only_mock: false`.

Attempt 16 adds the missing Hallucinate dashboard to Swissknife MCP consumer
launch receipt. The Hallucinate interoperability spec and Swissknife MCP
Playwright spec both load the same Hallucinate-owned receipt fixture, verify
the VAI-512/VAIOS-G723 lineage, assert the three dashboard MCP backends,
require all six mediated `tools/list` and `tools/call` operations, keep the
shared `mcp_server_invocation_receipt_v1` consumer receipt schema, and reject
dashboard-only mocks or duplicate catalog schemas. The Swissknife standalone
consumer validator also reads the receipt during `npm --prefix swissknife run
test:e2e:mcp`, so the same evidence is exercised by both applications.

Attempt 15 validation evidence:

- Hallucinate headless backend gate passed 5 backend Playwright tests for the
  dashboard catalog, mediated receipts, launch-readiness fixture, and
  Swissknife fixture parity. The Electron UI tests were skipped because this
  environment has no `DISPLAY` or `WAYLAND_DISPLAY`.
- Swissknife `test:e2e:mcp` consumed the same VAI-512 fixture and proved one
  catalog schema, three backend packages, six operations, VAI-512 provenance,
  MCP++ descriptor evidence, and no dashboard-only mocks.
- Multimodal control-surface Playwright validation passed all 4 hardware-free
  mediation tests.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
