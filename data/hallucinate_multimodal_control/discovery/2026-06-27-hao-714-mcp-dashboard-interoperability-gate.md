# HAO-714 MCP Dashboard Interoperability Gate

Date: 2026-06-27
Task: HAO-714
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-27-hao-714-objective-gap-7ea369464239.md
VAI mirror: data/virtual_ai_os/discovery/2026-06-27-vai-531-mcp-dashboard-interoperability-gate.md

## Gate

This Hallucinate backlog mirror keeps HAO-714 aligned with the VAI-531
Hallucinate MCP dashboard interoperability console launch gate.

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/test/e2e/fixtures/vai-531-mcp-dashboard-interoperability-gate.json`
  records the shared dashboard interoperability receipt for VAIOS-G723.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` validates
  the dashboard capability catalog, daemon health paths, `tools/list`,
  `tools/call`, mediated receipts, Swissknife consumer handoff, and Playwright
  coverage.
- Any catalog normalization, dashboard UI wiring, mediated tool-call receipts,
  Swissknife consumers, Playwright coverage, dashboard backend validation, or
  supervisor-generated follow-up subtasks failure remains launch-gate work for
  the supervisor-fed backlog.

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
- ipfs_kit_py
- ipfs_datasets_py
- ipfs_accelerate_py
