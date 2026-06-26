# VAI-512 MCP Dashboard Consumption Evidence

Hardware-free validation covers the Hallucinate App dashboard capability catalog for
`ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.

- Hallucinate source: `hallucinate_app.mcp_dashboard_capability_catalog.v1`
- Mediated operations: `tools/list`, `tools/call`
- Control plane: `interaction_envelope`, `policy_decision`, `mediation_receipt`
- Swissknife consumer: binds by `daemon_id` and `server_package` to the existing
  `swissknifeMCPCapabilityRegistry`
- Schema policy: Swissknife consumes the Hallucinate catalog as an input and emits
  `swissknife.mcp_dashboard_consumption_binding.v1`; it does not define a second
  dashboard capability catalog schema.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
