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

