# VAI-512 Hallucinate MCP dashboard control-plane receipt

- Task: VAI-512
- Surface: Hallucinate App MCP dashboard tools
- Hardware required: false

## Control-plane proof

The Hallucinate daemon manager now mediates dashboard `tools/list` and `tools/call` requests with the same `ControlSurfaceInvocationGate.beforeInvoke` path used by daemon-managed MCP service invocations. The Playwright replay enables an explicit test-only policy evaluator with `HALLUCINATE_APP_E2E_ALLOW_DASHBOARD_MCP=true`, then verifies that each of `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` returns:

- an `interaction_envelope`
- an `allow` `policy_decision`
- a `mediation_receipt`
- a dashboard tool-call receipt with `dashboard_only_mock: false`
- a stable `sha256:mcp_daemon_receipt:*` receipt CID

The replay intentionally uses safe probe metadata only and does not require GPUs, cameras, glasses, daemon hardware, or model inference.
