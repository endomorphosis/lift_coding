# VAI-512 Control Plane MCP Dashboard Evidence

- Task: VAI-512
- Control plane hook: `hallucinate_app.node.control_surface_invocation.ControlSurfaceInvocationGate.beforeInvoke`
- Shared receipt schema: `mcp_dashboard_tool_mediation_receipt_v1`
- Hardware requirement: none

## Proof points

- `tools/list` and `tools/call` requests are normalized as control-surface
  invocations before dispatch.
- The receipt records `interaction_envelope_id`, `policy_decision_id`,
  `mediation_receipt_id`, `daemon_id`, `server_package`, `tool_protocol`,
  `safe_probe`, and `receipt_cid`.
- The hardware-free dispatcher records upstream URL, method, path, and safe-probe
  metadata without using dashboard-only mocks.
