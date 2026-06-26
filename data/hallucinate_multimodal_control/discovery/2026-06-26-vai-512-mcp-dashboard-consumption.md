# VAI-512 Hallucinate MCP Dashboard Mediation

Hallucinate App now exposes a catalog-backed mediated dashboard tool path for
all three Python MCP dashboard servers:

- `ipfs_kit_py` through `ipfs-kit`
- `ipfs_datasets_py` through `ipfs-datasets`
- `ipfs_accelerate_py` through `ipfs-accelerate`

Dashboard `tools/list` and safe `tools/call` probes dispatch through
`MCPDaemonManager.invokeDashboardToolProtocol`, which calls the shared
`ControlSurfaceInvocationGate.beforeInvoke` hook before transport execution.
The renderer preload receives receipts containing the policy decision and
mediation receipt instead of making dashboard-only mock calls.
