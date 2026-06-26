# HAO-704 Launch Playwright Validation Gate

Date: 2026-06-26
Task: HAO-704
Goal id: VAIOS-G725
Evidence term: launch Playwright validation gate

HAO-704 closes the Hallucinate-owned VAIOS-G725 objective gap by binding
Swissknife's MCP++ dashboard consumer contract to the launch Playwright
validation gate. The proof consumes the shared Hallucinate App dashboard
capability catalog and requires all three backend MCP server packages:
`ipfs_accelerate_py`, `ipfs_datasets_py`, and `ipfs_kit_py`.

## Gate

```text
npm --prefix swissknife run test:e2e:mcp
```

The task-level launch command remains:

```text
npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

## Evidence

- `swissknife/test/e2e/mcp-dashboard.spec.ts` validates the shared Hallucinate App dashboard capability catalog through the Swissknife MCP capability registry.
- `swissknife/test/e2e/fixtures/hao-704-mcp-dashboard-launch-gate.json` records the VAIOS-G725 launch readiness receipt for the HAO-704 supervisor gap.
- `swissknife/build-tools/configs/playwright.mcp-dashboard.config.ts` keeps the MCP dashboard gate scoped to the API-level Playwright spec without launching the desktop web server.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` remains in the `test:e2e:mcp` command after the Playwright spec and asserts the HAO-704 receipt.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records the HAO-704 proof on VAIOS-G725.

## Covered Terms

- Swissknife applications
- Mcp-Plus-Plus
- MCP++ compatibility
- MCP server dashboard
- dashboard capability catalog
- ipfs_accelerate_py
- ipfs_datasets_py
- ipfs_kit_py
- tools/list
- tools/call
- control plane
- launch Playwright validation gate
