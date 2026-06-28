# MGW-546 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

## Gate

MGW-546 binds the `VAIOS-G723` Hallucinate MCP dashboard interoperability
console to the launch Playwright validation gate after the objective scanner
found the missing gate receipt in
`data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-objective-gap-7ea369464239.md`.

The focused dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The repair keeps the same launch gate visible to the supervisor and to
Swissknife consumers:

```text
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes `MGW-546` in `launch_validation_gates` for `VAIOS-G723`, with the source objective gap receipt, this launch gate receipt, the Hallucinate backlog receipt, the shared JSON fixture, child goals, and follow-up subtasks.
- `hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json` records the same dashboard capability catalog schema, backend packages, daemon health paths, `tools/list`, `tools/call`, control_surface receipt requirements, and Swissknife consumer refs.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` remains parity-checked against `MCPDaemonManager.getDashboardCapabilityCatalog()` so Hallucinate App and Swissknife consume one shared catalog.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts this receipt, the Hallucinate backlog receipt, the shared catalog, and the readiness document before the launch Playwright validation gate can pass.

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
