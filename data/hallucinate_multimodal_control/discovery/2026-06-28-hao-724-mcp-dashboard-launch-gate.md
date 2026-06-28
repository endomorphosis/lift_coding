# HAO-724 MCP Dashboard Launch Gate

Date: 2026-06-28
Task: HAO-724
Virtual task: VAI-542
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-28-hao-724-objective-gap-7ea369464239.md

HAO-724 mirrors the VAI-542 Hallucinate MCP dashboard launch gate for the
Hallucinate supervisor backlog. It preserves the same child goals, backend
package requirements, mediated receipt route, and Playwright command set used
by the Virtual AI OS objective heap.

## Gate Fixture

```json
{
  "task_id": "VAI-542",
  "backlog_task_id": "HAO-724",
  "goal_id": "VAIOS-G723",
  "evidence_term": "launch Playwright validation gate",
  "hallucinate_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-724-objective-gap-7ea369464239.md",
  "hallucinate_launch_gate_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-724-mcp-dashboard-launch-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/vai-542-mcp-dashboard-launch-gate.json",
  "playwright_gate": "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
  "failure_rule": "Any dashboard catalog, UI wiring, mediated tools/list, mediated tools/call, Swissknife consumer, backend validation, or Playwright failure remains supervisor-generated follow-up work for VAIOS-G723."
}
```

## Covered Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- daemon health
- MCP++ telemetry
- tools/list
- tools/call
- control_surface receipts
- launch Playwright validation gate

## Validation Chain

```text
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for VAIOS-G723.
