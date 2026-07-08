# HAO-744 MCP Dashboard Launch Gate

Date: 2026-07-08
Task: HAO-744
Goal id: VAIOS-G724
Packet goals: VAIOS-G724, VAIOS-G728
Packet sibling: HAO-745 / VAIOS-G728
Evidence term: launch Playwright validation gate
Gate state: gate_open_until_playwright_passes

HAO-744 closes the Hallucinate App MCP dashboard capability catalog objective
gap by binding the dashboard capability catalog, menu-backed dashboards,
daemon health, mediated `tools/list`, mediated `tools/call`, and Swissknife
catalog consumer to the launch Playwright validation gate. The proof keeps the
supervisor-fed backlog aligned with `goal_packet/launch/hallucinate_app/44dceea6bc53`
and preserves the HAO-745 / VAIOS-G728 daemon launch packet sibling through the
shared catalog entry.

## Required Evidence

- hallucinate_app menus
- Hallucinate App MCP dashboard
- dashboard capability catalog
- daemon health
- tools/list
- tools/call
- ipfs_accelerate_py MCP server
- ipfs_datasets_py MCP server
- ipfs_kit_py MCP server
- Swissknife applications
- Playwright MCP dashboard interoperability
- launch Playwright validation gate

## Validation Gate

```sh
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

The executable dashboard slice is:

```sh
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Catalog Contract

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-744",
  "goal_id": "VAIOS-G724",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goal_ids": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "packet_sibling_task_id": "HAO-745",
  "packet_sibling_goal_id": "VAIOS-G728",
  "lineage_id": "VAIOS-G724:hallucinate-mcp-dashboard-capability-catalog",
  "source_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-744-objective-gap-3e00ad2a0074.md",
  "launch_gate_receipt": "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-744-mcp-dashboard-launch-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/hao-744-mcp-dashboard-launch-gate.json",
  "catalog_fixture": "hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json",
  "evidence_term": "launch Playwright validation gate",
  "gate_state": "gate_open_until_playwright_passes",
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "required_evidence": [
    "hallucinate_app menus",
    "Hallucinate App MCP dashboard",
    "dashboard capability catalog",
    "daemon health",
    "tools/list",
    "tools/call",
    "ipfs_accelerate_py MCP server",
    "ipfs_datasets_py MCP server",
    "ipfs_kit_py MCP server",
    "Swissknife applications",
    "Playwright MCP dashboard interoperability",
    "launch Playwright validation gate"
  ]
}
```

## Evidence Files

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` emits the HAO-744 `launch_validation_gates` entry from `getDashboardCapabilityCatalog`.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` asserts the Electron-exposed and headless dashboard capability catalog includes HAO-744 and its HAO-745/VAIOS-G728 packet sibling.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` validates this receipt, the JSON fixture, the July 8 objective gap receipt, and the objective heap proof.
- `hallucinate_app/test/e2e/fixtures/hao-744-mcp-dashboard-launch-gate.json` snapshots the HAO-744 gate from the production catalog.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` snapshots the full shared catalog consumed by Hallucinate App and Swissknife.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` asserts Swissknife consumes the same HAO-744 catalog entry.

## Failure Rule

Any missing HAO-744 launch Playwright validation gate, catalog, daemon health,
`tools/list`, `tools/call`, Swissknife consumer, or HAO-745 packet sibling
evidence remains supervisor-fed launch work for VAIOS-G724 and VAIOS-G728.
