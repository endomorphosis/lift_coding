# MGW-547 Attempt 8 Launch Playwright Validation Gate

Date: 2026-06-28
Task: MGW-547
Attempt: 8
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-547-objective-gap-7ea369464239.md
Receipt fixture: hallucinate_app/test/e2e/fixtures/mgw-547-mcp-dashboard-launch-gate.json

## Gate

MGW-547 attempt 8 keeps the Hallucinate MCP dashboard interoperability console
bound to the launch Playwright validation gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The gate remains open until the shared dashboard capability catalog proves the
backend service catalog, daemon health, MCP++ telemetry, mediated `tools/list`,
mediated `tools/call`, and `control_surface` receipts for `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py`.

## Evidence Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- tools/list
- tools/call

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Failure Rule

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
