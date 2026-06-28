# MGW-547 Hallucinate Backlog Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-547
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-547-objective-gap-7ea369464239.md

## Gate

This Hallucinate backlog mirror keeps the MGW-547 objective gap aligned with
the Hallucinate App MCP dashboard validation gate.

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/test/e2e/fixtures/mgw-547-mcp-dashboard-launch-gate.json`
  records the shared `launch_readiness_receipt_v1` payload.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` validate
  catalog normalization, dashboard UI wiring, daemon health, `tools/list`,
  `tools/call`, mediated receipts, and Swissknife consumer handoff.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` keeps the
  VAIOS-G723 child goals visible to the supervisor-fed backlog.

## Covered Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- tools/list
- tools/call
