# VAI-512 MCP dashboard consumption evidence

- Task: VAI-512
- Goal: VAIOS-G723
- Validation lane: objective/launch/mcp-dashboard-consumption
- Hardware required: false

## Evidence added

- Hallucinate App exposes `hallucinate_app.mcp_dashboard_capability_catalog.v1` through `window.electronAPI.daemon.getDashboardCapabilityCatalog()`.
- The catalog includes `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` with live dashboard URLs, `tools/list`, `tools/call`, safe probe metadata, Swissknife consumer labels, and `control_surface_contract:mcp-daemon:*` mediation contracts.
- Hallucinate App now exposes mediated dashboard tool calls through:
  - `window.electronAPI.daemon.mediateDashboardToolsList(daemonId, invocation)`
  - `window.electronAPI.daemon.mediateDashboardToolsCall(daemonId, invocation)`
- The mediated call receipt format is `mcp_dashboard_tool_call_receipt_v1` and includes `interaction_envelope_id`, `policy_decision_id`, `mediation_receipt_id`, `dispatch_allowed`, and `receipt_cid`.
- Swissknife consumes the Hallucinate dashboard catalog schema directly via `consumeHallucinateDashboardCapabilityCatalog`, mapping catalog entries to existing Swissknife MCP capability descriptors without a duplicate catalog schema.

## Validation commands

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
