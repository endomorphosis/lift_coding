# Visual check — SwissKnife GUI ↔ MCP++ GUI surfaces (2026-10-13)

Method: the live virtual desktop (`swissknife/web/`, the same tree the
agent-supervisor target names as its live target) was served statically on
127.0.0.1:8901 and driven with Playwright 1.55 + its Chromium headless shell
(build 1187, the build doc 49 pins). The preinstalled `/opt/meta-chromium`
build could not be used: it rejects loopback navigation with
`ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS` even with the standard
LocalNetworkAccess disable flags. No gateway/backend was running, so the
gateway API calls (`/mcp/tools/bindings`, `/mcp/apps/backend-status`,
`/mcp/services/*/mcp/health|helia/status`) return 404 — every surface below
is therefore shown in its designed degraded/unavailable state, which is
itself one of the states the IR mapping requires (doc 49: deterministic
loading, ready, empty, failure, and service-availability states). Capture
logs: `capture_log.json`, `capture_log2.json`, `probe2.json`.

## Screenshots

- `01-virtual-desktop.png` — The virtual desktop renders cleanly: full icon
  grid including the interfacing apps (MCP Control, MCP++ Explorer,
  Supervisor, ORB UI, IDL Explorer, Datasets, Accelerate), taskbar with
  clock. No render errors.
- `02-agent-supervisor-console.png` — Agent Supervisor console window.
  Header controls Contract / Security / Refresh / Empty / Error; status
  strip STATUS **degraded**, ACTIVE GOALS 2, QUEUED 4, RUNNING 1, MODE
  **fallback** (the console fell back to local data when the gateway control
  catalog 404'd, exactly the designed service-availability behavior; launch
  logged `Gateway control catalog returned HTTP 404` from
  `js/live-tool-gateway.js`). Goals tree, queue, active-task detail and the
  Active task / Dispatch / Steering / Receipts / Health tabs all render —
  matching the semantic baseline's components and actions
  (comp:console-root, submit-steering, submit-dispatch, persist-receipt…).
- `04-mcp-control.png`, `05-mcp-control-alone.png` — MCP Server Control
  Center (opened over the console, then alone; identical result): toolbar
  (Refresh / Templates / Add Host Daemon / Add Browser Remote / Discovery /
  Metrics), Auto-discovery ON, a libp2p chip, Categories (All Servers 0,
  Host Daemon 0, Browser Remote 0, Core 0, Integrations 0, Databases 0,
  Cloud 0, Custom 0), footer "Active Host Daemons: 0". Correct designed
  empty state: with no gateway, the dashboard records zero daemons rather
  than fabricating any (browser-truth policy SWR-027). **Defect found —
  see "Mismatch" below.**
- `06-mcp-plus-plus-app.png` — MCP++ Explorer (the MCP++ GUI surface):
  "Live protocol state and explicit tool exchange across the configured
  IPFS services", status UNAVAILABLE, "0/3 MCP++ services responded",
  service cards **IPFS Kit / IPFS Datasets / IPFS Accelerate** (0 tools,
  "not negotiated") — exactly the three services the MCP++ descriptors
  name — tabs Overview / Tools / Protocol / Diagnostics / Events / Policy /
  Artifacts, Protocol Coverage panel, and VDA-G053 Diagnostics (Peer
  Diagnostics citing `ipfs_kit_py`, `ipfs_datasets_py`,
  `ipfs_accelerate_py`, libp2p peer id `12D3KooWMCPPPG053`, a `did:key:`
  identity, Event DAG frontier). Renders its designed unavailable state
  with correct descriptor content; its 31 console errors are the expected
  failed probes of the three services' health/helia endpoints.
- `07-agent-supervisor-steering.png`, `09-agent-supervisor-steering-invalid-max.png`
  — Steering tab (small window, then maximized): "Prompt steering" form for
  the governed-steering goal, steering-prompt textarea, NORMALIZED TARGET,
  POLICY CLASS **confirm**, AFFECTED TASKS, PROMPT SIZE 0/8000, and the
  **Planned MCP action `agent_supervisor.prompt_steering.request` —
  "ipfs_accelerate_py via mcp, mcp++"**, with preflight list
  (target_authorization, task_dependencies, branch_protection,
  confirmation_policy, execution_budget, receipt_persistence), Dry run and
  Confirm checkboxes, and a Submit control held `aria-disabled` until
  confirmation — the mapping's confirm-gated dispatch, visible.
- `08-agent-supervisor-steering-invalid.png`, `10-agent-supervisor-steering-error.png`
  — The steering form driven into its validation state (confirm checked,
  submit clicked with an empty prompt): a red `role="alert"` banner
  **`scope_not_allowed` — "Prompt text must be present and no longer than
  8000 characters."** with a "Review request and retry" button. DOM
  verification at that moment: the textarea carries
  `aria-invalid="true" aria-describedby="agent-supervisor-steering-error"
  aria-errormessage="agent-supervisor-steering-error"`, and the Submit
  button carries `aria-describedby="agent-supervisor-steering-error"`.
  **Field-to-error association works live** — the behavior the refreshed
  semantic baseline now records (the source gained the association
  attributes, which is why `missing-field-error-association` left the
  known-pre-change-failures list during this pass).

## Mismatch found (documented, not fixed — presentation layer)

MCP Control window header (`05-mcp-control-alone.png`): small status-legend
fragments (colored dots with clipped text pieces such as "daemon",
"browser", "commands", "remote") overlap the "MCP Server Control Center"
title at the window's top-left and are clipped, and the category rows other
than "All Servers" render at very low contrast. Structure from DOM
geometry: `.window-content` (798×566) → `.window-app-content` (798×2140,
clipped) → `.mcp-control-app.enhanced` → `.mcp-header` (798×140); the
fragments live inside the header band. No stylesheet failed to load (the
only 404s are the gateway APIs above and the PWA `offline.html` /
`manifest.webmanifest`). The app's data behavior is correct (designed
empty state, browser-truth policy honored); this is a pre-existing
cosmetic layout defect in the legacy dashboard app's header, unrelated to
the receipt-schema / descriptor / P2P-transport interfacing surface, and
outside the scoped fix set of this pass. Recorded here for a future
MCP Control UI cleanup.

## Verdict

All three interfacing views named in the mapping exist, render without
blocking errors, and bind to the contracts/descriptors the mapping says
they should: the console to the supervisor gateway contract family (with
designed degraded/fallback states), the MCP++ Explorer to the three IPFS
service descriptors, and MCP Control to the browser-truth daemon policy.
The one live-behavior property this pass depended on — steering
field-to-error association — is verified working in the running app.
