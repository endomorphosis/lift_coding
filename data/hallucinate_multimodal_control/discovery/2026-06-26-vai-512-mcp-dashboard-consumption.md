# VAI-512 Hallucinate MCP Dashboard Consumption Evidence

Task: VAI-512
Goal id: VAIOS-G723

The MCP dashboard validation path now proves the control-surface mediation
surface for dashboard tools end to end:

- `MCPDaemonManager.getDashboardCapabilityCatalog()` exposes
  `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` dashboard
  capabilities.
- `dashboardToolsList()` and `dashboardToolsCall()` mediate through
  `ControlSurfaceInvocationGate` and preserve `interaction_envelope`,
  `policy_decision`, `mediation_receipt`, and `receipt_cid` evidence.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` consumes the same
  catalog fixture and rejects duplicate catalog schemas or dashboard-only
  mocks.
- `hallucinate_app/test/e2e/fixtures/vai-512-hallucinate-swissknife-mcp-dashboard-consumption.json`
  is the shared Hallucinate dashboard to Swissknife MCP consumer launch receipt.

Attempt 15 keeps the fixture aligned with the live Hallucinate daemon manager
catalog for the shared interoperability surface: VAI-512 provenance,
dashboard-only mock rejection, `tools/list`, `tools/call`, safe probes,
control-surface receipt requirements, MCP++ descriptor evidence, and
dashboard receipt consumer refs.

Attempt 16 binds the missing receipt evidence directly into both application
validators. Hallucinate `mcp-dashboard-interoperability.spec.ts` runs the
Swissknife MCP consumer command and checks the VAI-512 receipt against the
returned package and operation payload. Swissknife `mcp-dashboard.spec.ts` and
`scripts/test-mcp-dashboard-consumer.cjs` read the same Hallucinate-owned
receipt and assert VAIOS-G723 lineage, all three dashboard MCP backends,
`tools/list`, `tools/call`, control-plane mediation fields, one catalog schema,
and no dashboard-only mocks.

Headless validation result:

- `mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts`: 5
  backend tests passed, Electron UI tests skipped due missing display server.
- `swissknife test:e2e:mcp`: passed with three backend packages and six
  dashboard MCP operations.
- `multimodal-control-surface.spec.ts`: 4 tests passed.

Fixture:

```text
hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json
```

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
