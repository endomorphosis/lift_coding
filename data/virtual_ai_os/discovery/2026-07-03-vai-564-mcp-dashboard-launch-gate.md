# VAI-564 MCP Dashboard Launch Gate

Date: 2026-07-03
Task: VAI-564
Goal id: VAIOS-G724
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-07-03-vai-564-objective-gap-3e00ad2a0074.md

## Gate

VAI-564 closes the current Virtual AI OS objective gap for the Hallucinate App
MCP dashboard capability catalog by binding the scanner-visible objective
receipt to the shared Hallucinate App launch Playwright validation gate and the
Swissknife consumer catalog.

The focused dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full launch packet command remains:

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
  `VAI-564` launch gate in `DASHBOARD_LAUNCH_VALIDATION_GATES` and the shared
  `getDashboardCapabilityCatalog()` output with `gate_state:
  gate_closed_by_playwright_validation`, `packet_sibling_goal_id: VAIOS-G728`,
  and packet goals `VAIOS-G724` and `VAIOS-G728`.
- `hallucinate_app/test/e2e/fixtures/vai-564-mcp-dashboard-launch-gate.json`
  records the launch readiness receipt for `VAIOS-G724`, the packet sibling
  daemon launch objective `VAIOS-G728`, the dashboard capability catalog, and
  the three MCP server dashboards.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` is
  regenerated from the live Hallucinate manager so Swissknife and the
  Hallucinate dashboard tests consume the same `launch_validation_gates` entry.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` assert
  the VAI-564 gate against the live catalog, daemon health, `tools/list`,
  `tools/call`, `Playwright MCP dashboard interoperability`, and the
  `launch Playwright validation gate`.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` verifies the VAI-564
  gate from the Swissknife side so `Swissknife applications` consume the same
  dashboard capability catalog without duplicate schemas or dashboard-only
  mocks.
- The external backend surfaces remain in scope through `external/ipfs_kit`
  (`ipfs_kit_py`), `external/ipfs_datasets` (`ipfs_datasets_py`), and
  `external/ipfs_accelerate` (`ipfs_accelerate_py`), which are represented in
  the catalog as the `ipfs-kit`, `ipfs-datasets`, and `ipfs-accelerate`
  dashboards and safe-probe MCP tool routes.

## Gate State

`gate_closed_by_playwright_validation`. Any missing catalog entry, daemon
health route, MCP tool operation, Swissknife handoff, or Playwright proof
reopens launch work for `VAIOS-G724` and packet sibling `VAIOS-G728`.

## Validation

The VAI-564 launch gate is validated by:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The packet-level guard also keeps the optional Swissknife Meta glasses and
Hallucinate multimodal control surface checks in the same chain when those
submodules are present:

```text
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
