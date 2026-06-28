# MGW-546 Hallucinate Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

## Gate

This Hallucinate backlog receipt mirrors the MGW-546 launch gate for the
`VAIOS-G723` Hallucinate MCP dashboard interoperability console. It keeps the
Hallucinate App dashboard, Swissknife catalog consumer, and supervisor-generated
follow-up subtasks aligned on the same validation command:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the `MGW-546` launch gate in the shared dashboard capability catalog.
- `hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json` binds the fixture to catalog normalization, dashboard UI wiring, mediated `tools/list` and `tools/call` receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks.
- `data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-launch-playwright-validation-gate.md` is the paired launch gate receipt for the source objective gap.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts this receipt beside the Meta glasses receipt and readiness document so dashboard validation failures remain visible to the supervisor.

## Covered Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- dashboard capability catalog
- daemon health
- MCP++
- tools/list
- tools/call
- ipfs_kit_py
- ipfs_datasets_py
- ipfs_accelerate_py
- Swissknife
