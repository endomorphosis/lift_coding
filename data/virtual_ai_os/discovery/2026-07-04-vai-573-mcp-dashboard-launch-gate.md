# VAI-573 MCP Dashboard Launch Gate

Date: 2026-07-04
Task: VAI-573
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-07-04-vai-573-objective-gap-3e00ad2a0074.md

## Gate

VAI-573 closes the current Virtual AI OS objective gap for the Hallucinate App
MCP dashboard capability catalog by binding the VAIOS-G724 scanner receipt to
the shared Hallucinate App launch Playwright validation gate, the Swissknife
catalog consumer, and the VAIOS-G728 daemon launch packet sibling.

Focused dashboard gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

Full launch packet gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

## Covered Terms

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

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the
  `VAI-573` launch gate in `DASHBOARD_LAUNCH_VALIDATION_GATES` and the shared
  `getDashboardCapabilityCatalog()` output with `gate_state:
  gate_closed_by_playwright_validation`, `packet_sibling_goal_id: VAIOS-G728`,
  and packet goals `VAIOS-G724` and `VAIOS-G728`.
- `hallucinate_app/test/e2e/fixtures/vai-573-mcp-dashboard-launch-gate.json`
  is generated from the live Hallucinate manager and records the dashboard
  launch readiness receipt, three backend dashboard handoff records, safe
  `tools/list` and `tools/call` probes, and Swissknife consumer route.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` is
  regenerated from the same manager catalog so Hallucinate and Swissknife tests
  consume one schema and one `launch_validation_gates` source of truth.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` assert the
  VAI-573 launch gate against the live catalog, dashboard capability catalog,
  daemon health, `tools/list`, `tools/call`, packet goals, and the launch
  Playwright validation gate.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` verifies the same
  VAI-573 gate and fixture from the Swissknife side, proving Swissknife
  applications consume the Hallucinate MCP dashboard capability catalog without
  duplicate schemas or dashboard-only mocks.
- The external backend surfaces remain represented by `external/ipfs_kit`
  (`ipfs_kit_py`), `external/ipfs_datasets` (`ipfs_datasets_py`), and
  `external/ipfs_accelerate` (`ipfs_accelerate_py`) through the `ipfs-kit`,
  `ipfs-datasets`, and `ipfs-accelerate` dashboard server entries.
- The packet sibling daemon evidence remains aligned through
  `data/virtual_ai_os/discovery/2026-07-04-vai-568-daemon-launch-health-gate.md`,
  which covers VAIOS-G728 daemon health, MCP server launch, dashboard catalog,
  and Swissknife handoff evidence for the same launch packet.

## Gate State

`gate_closed_by_playwright_validation`. Any missing catalog entry, daemon
health route, MCP tool operation, external backend handoff, Swissknife consumer,
or packet sibling proof reopens launch work for `VAIOS-G724` and `VAIOS-G728`.

## Validation

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
