# VAI-512 MCP Dashboard Consumption Evidence

- Task: VAI-512
- Goal: VAIOS-G723
- Receipt schema: `mcp_dashboard_tool_mediation_receipt_v1`
- Catalog schema: `hallucinate_app.mcp_dashboard_capability_catalog.v1`
- Hallucinate evidence: `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`
- Swissknife evidence: `swissknife/test/e2e/mcp-dashboard-consumption.spec.ts`

## Covered MCP dashboards

- `ipfs_kit_py` via `ipfs-kit`
- `ipfs_datasets_py` via `ipfs-datasets`
- `ipfs_accelerate_py` via `ipfs-accelerate`

## Validation route

The Hallucinate daemon manager publishes one dashboard capability catalog, mediates
both `tools/list` and `tools/call` through `ControlSurfaceInvocationGate`, and emits
hardware-free receipts with `dashboard_only_mock: false`.

Swissknife consumes that same catalog with
`buildSwissknifeMCPRegistryFromDashboardCatalog`, preserving one catalog schema and
one mediated tool-call receipt schema while mapping the entries onto existing
Swissknife MCP capability descriptors.
