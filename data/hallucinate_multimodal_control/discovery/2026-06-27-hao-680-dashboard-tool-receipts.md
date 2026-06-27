# HAO-680 Dashboard Tool Invocation Receipts

Date: 2026-06-27
Task: HAO-680
Goal: VAIOS-G723
Bundle: objective/launch/hallucinate-mcp-dashboard
Depends on: HAO-677

## Receipt Path

Dashboard-originated `tools/list` and safe `tools/call` probes now use the same
pre-transport control surface route as Swissknife MCP consumers:

1. `interaction_envelope`
2. `policy_decision`
3. `mediation_receipt`
4. supervised MCP server transport

The shared entry points are:

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js`
  - `dashboardToolsList(daemonId)`
  - `dashboardToolsCall(daemonId)`
  - `invokeManagedService(daemonId, invocation, invoker)`
- `hallucinate_app/hallucinate_app/node/control_surface_invocation.js`
  - `ControlSurfaceInvocationGate.beforeInvoke()`
  - `ControlSurfaceInvocationGate.invoke()`

## MCP++ Evidence

Each dashboard capability catalog entry carries `MCP++ descriptor/profile evidence`
through `mcpplusplus_descriptor_evidence`. The mediation receipt preserves that
evidence under `mediation_receipt.metadata.mcpplusplus` so Hallucinate App,
Swissknife, and launch-readiness packets can consume the same descriptor/profile
record when it is advertised, or the explicit `not_advertised` evidence when it is
not.

## Receipt Consumers

Receipt ids are exposed for:

- `hallucinate_app.electron.dashboard`
- `hallucinate_app.swissknife.mcp_capability_registry`
- `launch_readiness_packet:VAIOS-G723`
- `launch_readiness_packet:VAIOS-G724`
- `launch_readiness_packet:VAIOS-G728`

The Playwright gate asserts `receipt_id`, `decision_id`, `interaction_id`, and
`receipt_cid` for `ipfs-kit`, `ipfs-datasets`, and `ipfs-accelerate` across both
`tools/list` and `tools/call`.

## Validation

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-dashboard-interoperability.spec.ts
rg -n "interaction_envelope|policy_decision|mediation_receipt|MCP\\+\\+|tools/list|tools/call|HAO-680" hallucinate_app swissknife tests data/hallucinate_multimodal_control/discovery
```

The first command passed in this worktree on 2026-06-27 with 10 passed and 5
Electron UI tests skipped because no graphical display or `xvfb-run` was
available.
