# HAO-680 Dashboard MCP++ and control_surface Receipts

HAO-680 routes dashboard-originated `tools/list` and safe `tools/call` probes
through the same Hallucinate App mediation path used by Swissknife:

```text
interaction_envelope -> policy_decision -> mediation_receipt -> supervised MCP server transport
```

## Receipt Evidence

- `hallucinate_app/hallucinate_app/node/control_surface_invocation.js` now emits
  stable `receipt_id` and `receipt_cid` values plus a `receipt_ids` bundle on
  every `mediation_receipt`.
- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` owns dashboard
  probe entrypoints for `tools/list` and `tools/call`, adds MCP++ descriptor and
  profile evidence where available, and attaches consumer refs for Hallucinate
  App, Swissknife, and the launch-readiness packet.
- `hallucinate_app/preload.js` and `hallucinate_app/index.js` expose the
  dashboard probe calls over the Electron daemon bridge used by the dashboard
  views.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` verifies
  both operations per backend and asserts `interaction_envelope`,
  `policy_decision`, `mediation_receipt`, `receipt_ids`, `receipt_cid`,
  `MCP++ descriptor/profile evidence`, `tools/list`, and `tools/call`.

## Consumers

Receipt consumer refs emitted by the dashboard catalog and mediation receipts:

```json
[
  "hallucinate_app.electron.dashboard",
  "hallucinate_app.swissknife.mcp_capability_registry",
  "launch_readiness_packet:VAIOS-G723",
  "mcp_daemon:<daemon_id>"
]
```

These refs make the same receipt IDs consumable by Hallucinate App dashboard
views, Swissknife catalog consumers, and the launch-readiness packet.
