# MGW-546 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

## Gate

MGW-546 binds the `VAIOS-G723` Hallucinate MCP dashboard interoperability
console to the shared launch Playwright validation gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The gate covers catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks for the `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py` dashboard servers.

## Evidence

- Source gap receipt: `data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-objective-gap-7ea369464239.md`
- Fixture: `hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json`
- Playwright spec: `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`
- Dashboard catalog: `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js`
- Objective heap: `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- Readiness doc: `docs/launch/phone_desktop_glasses_readiness.md`

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
