# Feature Matrix — SwissKnife Virtual Desktop, Live-Backend Verification

**Pass:** functional verification, 2026-10-13. Companion to
[`BROKEN_CONTRACT_MAP.md`](../BROKEN_CONTRACT_MAP.md) and `SWISSKNIFE_FIX_NOTES.md`.
**How:** the backend stack was stood up on loopback using the repos' own launch routes,
then the desktop was driven with headless Playwright (harness:
`visual_check/fv_state/drive.mjs`; per-app records: `fv_state/drive-apps.jsonl`).
Every feature below records intended behavior (ORB/IDL descriptors + intent_ir),
observed behavior, and the program state that proves agreement or exposes divergence.
New screenshots are the `fv-*.png` files in this directory (the earlier degraded-state
set, `01…10-*.png`, is untouched).

## Stack under test (all loopback, repos' own launch routes)

| Component | Route | Address | State |
|---|---|---|---|
| Desktop + gateway mediator | `vite dev --config vite.web.config.ts` | 127.0.0.1:3001 | serves `web/`; `/mcp/tools/bindings`, `/mcp/apps/backend-status`, `POST /mcp/tools/call`, `/mcp/services/<owner>/mcp/*` proxy |
| ipfs_kit MCP (compat adapter) | `scripts/start-ipfs-kit-mcp-compat.cjs` | 127.0.0.1:8014 | 124 tools served (Python-discovered registry) |
| ipfs_datasets MCP (compat adapter) | `scripts/start-ipfs-datasets-mcp-compat.cjs` | 127.0.0.1:3002 | 319 tools served |
| ipfs_accelerate MCP (compat adapter) | `scripts/start-ipfs-accelerate-mcp-compat.cjs` | 127.0.0.1:3003 | 18 tools (facade + aliases; upstream live) |
| ipfs_accelerate upstream | `python -m ipfs_accelerate_py.mcp_server --fastapi` | 127.0.0.1:9000 | `/healthz` 200 |
| ipfs_datasets dashboard | `python -m ipfs_datasets_py.dashboards.launch_mcp_dashboard` | 127.0.0.1:8899 | required by the datasets adapter's generic dispatch (see F-13) |

Bring-up is idempotent and preserved at `fv_state/bring-up.sh`. Program-state captures
(bindings, backend-status matrix, per-service `tools/list`, health) are in `fv_state/*.json`.

## Headline features

### F-01 — Desktop boot and window lifecycle
- **Intended:** desktop shell loads; apps launch into windows that can be focused and
  closed (manifest-driven, 45 canonical apps).
- **Observed:** desktop boots (`window.desktop` ready); **45/45 canonical apps opened,
  focused, and closed cleanly** through the same `desktop.launchApp` / `focusWindow` /
  titlebar-close path a user takes. 0 sweep errors.
- **Program state:** `fv_state/drive-apps.jsonl` (45 records, `opened && closed` true);
  screenshot `fv-01-desktop-live.png`, `fv-02-sweep-done.png`.
- **Verdict: PASS.**

### F-02 — Manifest alias ids (code-editor, strudel-grandma, p2p-chat-offline)
- **Intended:** 48 ids addressable (manifest aliases resolve to canonical apps).
- **Observed:** `desktop.launchApp(<alias>)` fails with `App <alias> not found`; the
  manifest resolver (`resolveVirtualDesktopAppId`) maps each alias to its canonical app,
  whose launch passes (F-01). The repo's own audit driver resolves before launching.
- **Program state:** console errors captured in `fv_state/drive-results.json`;
  resolver behavior covered by `virtual-desktop-app-manifest.test.ts`.
- **Verdict: PARTIAL — resolver-mediated path PASS; raw `launchApp(alias)` FAIL**
  (contract map X1; no user-facing symptom found — desktop icons/start entries use
  canonical ids).

### F-03 — MCP++ Explorer: service discovery
- **Intended (intent_ir + ORB/IDL):** with backends up, the Explorer negotiates all three
  configured services and discovers their tools — not the no-backend UNAVAILABLE state
  of the prior pass.
- **Observed:** all three services negotiated; **461 tools discovered** (Kit 124,
  Datasets 319, Accelerate 18) with MCP++ capability tags (`mcp++/p2p-transport`,
  `mcp++/mcp-idl`, `mcp++/cid-envelope`, `mcp++/ucan`, `mcp++/event-dag`). Header reads
  **DEGRADED — "2/3 MCP++ services responded"**.
- **Program state:** in-browser capture of the inspection traffic — `initialize`,
  `tools/list`, `interfaces/list`, `mcp++/dag/frontier`, `mcp++/dag/archives`,
  `mcp++/p2p/peers`, `/mcp/health`, `/mcp/helia/status` all 200; **`mcp++/risk/profile`
  → -32601 on all three adapters** (contract map R1 — the DEGRADED cause). Screenshot
  `fv-03-explorer-live.png`.
- **Verdict: PASS for discovery (the prior pass's failure mode is gone);
  DEGRADED status traced to refuted contract R1.**

### F-04 — MCP++ Explorer: explicit tool call
- **Intended:** the Tools tab runs an explicit call against a chosen service and shows
  the tool result.
- **Observed:** with the full datasets stack (adapter + dashboard :8899), calling
  `tools_list_categories` returned `isError: false`, HTTP 200 from the dashboard
  execute endpoint, with a real result payload. Without the dashboard, the same call
  surfaced a structured `isError` receipt naming the failed endpoint (fail-closed,
  no fake success). Screenshot `fv-04-explorer-tools.png`.
- **Program state:** adapter receipt JSON in both runs (adapter
  `swissknife-ipfs-datasets-compat`, tool `tools_dispatch`); direct adapter
  `tools/call` cross-check returned the real category catalog.
- **Verdict: PASS (full stack); the no-dashboard failure is correct fail-closed
  behavior for a missing stack component (contract map P13).**

### F-05 — MCP Control: live bindings + mediated invocation
- **Intended:** apps' live controls are `ready` when their owner backend is live, and
  invoking one executes through the gateway mediator with policy evaluation and a
  receipt (doc 48 §§4–5, 9).
- **Observed:** K/D/A panel shows all three owners **live** (mediated-gateway); the
  three `inspect tool registry` controls are `ready`. Invoking the datasets control
  **executed**: gateway `POST /mcp/tools/call` → 200, outcome `executed`, Policy
  `allow`, receipt CID `bafkreigwbyyyhfizc2bzhudfn57amu2mmkqmoichjjafwckf4mridq2nry`,
  Event-DAG id issued, real tool result (category catalog) returned to the panel.
  The Server Control Center half of the app truthfully shows 0 configured host
  daemons / 0 browser remotes (none configured in this profile), 8 templates, and a
  fully configured browser-libp2p defaults panel (8 configured, 0 gaps).
  Screenshots `fv-05-mcp-control-live.png`, `fv-10-mcp-control-invoke.png`.
- **Program state:** `GET /mcp/tools/bindings` = 79 controls, all `available`;
  correlation id `desktop:mcp-control.ipfs_datasets_py.inspect_tool_registry:…`
  recorded in the panel.
- **Verdict: PASS — the full mediated path (UI → gateway → policy → adapter → tool →
  receipt) works end to end.**

### F-06 — Agent Supervisor: console state
- **Intended:** goals tree, task queue, active task, receipts, and MCP++ health render
  from the supervisor contract; the app degrades to a browser-safe fallback when its
  console-gateway backend is absent.
- **Observed:** renders with STATUS `degraded` / MODE `fallback` (the supervisor
  console-gateway service was not part of the launched stack), 2 active goals
  (SWR-105, SWR-106 with subgoals), queue of 4, 1 running; K/D/A backend panel shows
  all owners `live` via the mediator and 3 MCP++ actions `ready`.
  Screenshot `fv-06-supervisor-live.png`.
- **Program state:** window DOM text + the app's own backend-status fetch
  (`/mcp/apps/backend-status?app_id=agent-supervisor` → `tool_backed`).
- **Verdict: PASS as designed degradation (fallback state is the documented behavior);
  the fallback is an environment-scope note, not a defect (contract map §4).**

### F-07 — Agent Supervisor: governed prompt steering through the confirm gate
- **Intended (SWR-106 + ORB coverage `steering_requires_confirmation: true`):** a
  steering prompt is normalized to a target, policy-classified, and only proceeds
  with explicit confirmation; dry-run produces the plan + receipt without mutating
  state.
- **Observed:** (1) Submit with neither checkbox set → **policy denial** on all three
  owner rows ("The operation was denied by policy. Review the decision and explicitly
  confirm if permitted."; Policy `not_evaluated`, Receipt `pending receipt`).
  (2) Submit with **Dry run** + **Confirm** set → normalized plan: target
  `task:SWR-105-1`, POLICY CLASS `confirm`, affected tasks listed, prompt size
  60/8000, planned MCP action `agent_supervisor.prompt_steering.request` via
  `ipfs_accelerate_py`, required proofs enumerated (target_authorization,
  task_dependencies, branch_protection, confirmation_policy, execution_budget,
  receipt_persistence), correlation id issued, receipt `rcpt-prompt-steer…` recorded.
  Screenshots `fv-07-supervisor-steering.png`, `fv-08-supervisor-confirm.png`,
  `fv-09-supervisor-dryrun.png`.
- **Program state:** panel text after each submit (captured verbatim in the pass log).
- **Verdict: PASS — the gate denies unconfirmed steering and admits confirmed
  dry-run steering with a receipt, exactly as the contract requires.**

### F-08 — Gateway program state (mediator routes)
- **Intended:** `/mcp/tools/bindings` reflects live discovery; `/mcp/apps/backend-status`
  gives every app a reasoned disposition.
- **Observed:** bindings = 79 controls / 79 available; backend-status = 45 apps,
  dispositions 38 tool_backed / 5 browser_local / 1 policy_blocked (api-keys) /
  1 external_provider; 135 statuses, every non-live status reasoned (contract map
  P1–P4, Z3-proved over this state).
- **Verdict: PASS.**

### F-09 — SVD-132 all-apps audit (repo's own real-browser runner)
- **Intended:** opens all 48 ids in a real browser and writes `svd-132-playwright.json`
  with 96 screenshots.
- **Observed:** after fixes F1/F2 the suite loads and executes, but exceeds its own
  900 s budget on this VM (two runs). The post-F1 run's evidence file was written
  (`svd-132-playwright.json`): 48 apps recorded, **0 passed / 48 failed**, 26 of 96
  screenshots captured — every app's close failed on the pre-F2 `desktop.closeWindow`
  TypeError (contract map R2, recorded per-app in that file), and the back ~34 apps'
  records are contaminated by the timeout teardown. 18 apps' complete screenshot
  sets are retained under
  `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots/svd-132-playwright/`.
- **Verdict: BLOCKED-BY-RUNTIME-BUDGET (contract map B1); superseded by F-01's sweep
  over the same desktop API.**

### F-10 — Apps whose runtime depends on external CDN egress
- `strudel-ai-daw`'s launch promise never settles because `@strudel.cycles` is fetched
  from `https://esm.sh`, which this VM's egress proxy refuses (`ERR_TUNNEL_CONNECTION_FAILED`);
  its window still registers, focuses, and closes. The desktop wallpaper (unsplash)
  fails the same way. **Verdict: environment-blocked (contract map B7), not app defects.**

## Per-app results (45 canonical + 3 aliases)

Generated from `fv_state/drive-apps.jsonl` (launch/focus/close sweep) joined with
`fv_state/backend-matrix.json` (backend disposition). "Live owners" = owners whose
backend status for the app is `live`.

| App | Backend disposition | Live owners | Launch | Close |
|---|---|---|---|---|
| terminal | tool_backed | kit, datasets, accelerate | PASS | PASS |
| vibecode | tool_backed | kit, datasets, accelerate | PASS | PASS |
| music-studio-unified | tool_backed | kit, accelerate | PASS | PASS |
| ai-chat | tool_backed | kit, datasets, accelerate | PASS | PASS |
| file-manager | tool_backed | kit, datasets | PASS | PASS |
| task-manager | tool_backed | datasets, accelerate | PASS | PASS |
| todo | tool_backed | kit, datasets | PASS | PASS |
| model-browser | tool_backed | kit, datasets, accelerate | PASS | PASS |
| huggingface | tool_backed | kit, datasets, accelerate | PASS | PASS |
| openrouter | tool_backed | datasets, accelerate | PASS | PASS |
| ipfs-explorer | tool_backed | kit | PASS | PASS |
| device-manager | tool_backed | kit, accelerate | PASS | PASS |
| settings | browser_local | — | PASS | PASS |
| mcp-control | tool_backed | kit, datasets, accelerate | PASS | PASS |
| api-keys | policy_blocked | — | PASS | PASS |
| github | tool_backed | kit, datasets | PASS | PASS |
| oauth-login | external_provider | — | PASS | PASS |
| cron | tool_backed | datasets, accelerate | PASS | PASS |
| navi | tool_backed | datasets | PASS | PASS |
| p2p-network | tool_backed | kit, accelerate | PASS | PASS |
| p2p-chat-unified | tool_backed | kit, datasets | PASS | PASS |
| neural-network-designer | tool_backed | kit, accelerate | PASS | PASS |
| training-manager | tool_backed | kit, datasets, accelerate | PASS | PASS |
| calculator | browser_local | — | PASS | PASS |
| clock | browser_local | — | PASS | PASS |
| calendar | tool_backed | kit, datasets | PASS | PASS |
| peertube | tool_backed | kit, accelerate | PASS | PASS |
| friends-list | tool_backed | kit, datasets | PASS | PASS |
| image-viewer | tool_backed | kit, accelerate | PASS | PASS |
| notes | tool_backed | kit, datasets | PASS | PASS |
| media-player | tool_backed | kit, accelerate | PASS | PASS |
| system-monitor | tool_backed | accelerate | PASS | PASS |
| neural-photoshop | tool_backed | kit, accelerate | PASS | PASS |
| cinema | tool_backed | kit, accelerate | PASS | PASS |
| strudel | tool_backed | kit, accelerate | PASS | PASS |
| strudel-ai-daw | tool_backed | kit, accelerate | PASS | PASS |
| music-studio | tool_backed | kit | PASS | PASS |
| p2p-chat | tool_backed | kit | PASS | PASS |
| datasets-browser | tool_backed | datasets | PASS | PASS |
| accelerate-panel | tool_backed | accelerate | PASS | PASS |
| idl-explorer | browser_local | — | PASS | PASS |
| glasses-preview | browser_local | — | PASS | PASS |
| orb-auto-ui | tool_backed | kit, datasets, accelerate | PASS | PASS |
| mcp-plus-plus | tool_backed | kit, datasets, accelerate | PASS | PASS |
| agent-supervisor | tool_backed | kit, datasets, accelerate | PASS | PASS |
| code-editor (alias → vibecode) | alias | — | FAIL raw / PASS via resolver | — |
| strudel-grandma (alias → strudel) | alias | — | FAIL raw / PASS via resolver | — |
| p2p-chat-offline (alias → p2p-chat) | alias | — | FAIL raw / PASS via resolver | — |

Notes on individual rows:
- `strudel-ai-daw`: Launch = PASS via the window-registration probe; its launch
  *promise* exceeds 20 s (esm.sh egress, F-10). Close = PASS.
- All other canonical rows: launch promise settled, window focused, closed via the
  titlebar control; zero console errors attributable to the app itself.
- Alias rows: see F-02 / contract map X1.

## Screenshot index (new, this pass)

| File | Shows |
|---|---|
| `fv-01-desktop-live.png` | Desktop booted against the live stack |
| `fv-02-sweep-done.png` | Desktop after the 48-id sweep |
| `fv-03-explorer-live.png` | MCP++ Explorer: 461 tools discovered, DEGRADED (R1) |
| `fv-04-explorer-tools.png` | Explorer Tools tab after the explicit call |
| `fv-05-mcp-control-live.png` | MCP Control: owners live, controls ready |
| `fv-06-supervisor-live.png` | Agent Supervisor console (fallback mode) |
| `fv-07-supervisor-steering.png` | Steering tab with the governed prompt form |
| `fv-08-supervisor-confirm.png` | Unconfirmed submit → policy denial |
| `fv-09-supervisor-dryrun.png` | Confirmed dry-run: normalized plan + receipt |
| `fv-10-mcp-control-invoke.png` | MCP Control after the executed mediated invocation |
