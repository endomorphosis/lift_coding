# MGW-546 Hallucinate Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

This Hallucinate-side receipt mirrors
`data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-launch-playwright-validation-gate.md`
for the Hallucinate MCP dashboard interoperability console.

The launch Playwright validation gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

It keeps catalog normalization, dashboard UI wiring, mediated tool-call receipts,
Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks tied to the shared dashboard catalog,
`tools/list`, `tools/call`, and the launch Playwright validation gate for
`ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.
