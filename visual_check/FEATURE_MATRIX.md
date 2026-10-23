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
- **Gap-closure update (2026-10-14): FIXED.** The served shell now resolves aliases
  inside `launchApp` (contract map X1). Live probe
  (`fv_state/alias_probe.mjs` → `alias-probe-results.json`): all 3 aliases open and
  close their canonical windows; canonical launches unchanged; unknown ids remain
  clean no-ops. **Verdict now: PASS (raw + resolver-mediated).**

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
- **Gap-closure update (2026-10-14): R1 FIXED; Explorer now fully healthy.**
  All three adapters answer the full Profile G surface including
  `mcp++/risk/profile` with genuine per-owner profiles (contract map R1/F3/G1).
  Cold full-stack restart + probe (`fv_state/explorer_probe.mjs` →
  `explorer-probe-results.json`, screenshot `fv-11-explorer-healthy.png`):
  header state **`ready`**, **"3/3 MCP++ services responded."**, 461 tools,
  capability tags negotiated on all three services. Availability note: the
  header count is `health.ok && initialize.ok` per service; under heavy VM
  CPU contention the client's 8 s probe timeout can still flap a service —
  an environment property, reproduced and measured, not a contract defect
  (warm adapter probes answer in milliseconds in a calm window).

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
- **Gap-closure update (2026-10-14): console now runs on its live gateway.**
  No separate console-gateway server exists in the repo; the production gateway
  is the desktop client's `createSupervisorGateway()` (its Profile G reads are
  what R1's fix made real), and the shell now installs it for the console
  (contract map §4/G3). Live probe (`fv_state/console_probe.mjs` →
  `console-probe-results.json`, screenshot `fv-12-supervisor-console-live.png`):
  status **`ready`**, transportMode **`degraded`** (not fallback), health
  `available` with all 3 backends live, queue/goals/receipts read **live**
  (0/0/0 — fallback sample data gone). The 5 remaining capability errors are
  the gateway's own deliberate non-mappings (`capability_unavailable`).
  **Verdict now: PASS live (with the gateway's typed partial mapping).**

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
- **Gap-closure update (2026-10-14): discharged in batches.** Three completed
  runs of the repo's own runner + driver over manifest batches (the runner's
  supported `manifest` option; scratch harness, deleted after use):
  **37/48 ids audited, 33 passed, 74/96 screenshots** — assembly at
  `fv_state/svd132-batched-assembly.json`. The F2 close path succeeds in
  every completed record. Failures: `terminal`, `github`, `media-player`
  (wallpaper egress only) and `strudel-ai-daw` (B7 esm.sh, verbatim).
  The last 11 ids were attempted twice more under load 18–39 on this
  2-core box and did not complete; the canonical single-run
  `svd-132-playwright.json` was not produced and its filename was left
  untouched. **Verdict now: PARTIAL-PASS (batched) — audit machinery and
  close path proven; single-run completion remains budget-blocked here.**

### F-10 — Apps whose runtime depends on external CDN egress
- `strudel-ai-daw`'s launch promise never settles because `@strudel.cycles` is fetched
  from `https://esm.sh`, which this VM's egress proxy refuses (`ERR_TUNNEL_CONNECTION_FAILED`);
  its window still registers, focuses, and closes. The desktop wallpaper (unsplash)
  fails the same way. **Verdict: environment-blocked (contract map B7), not app defects.**

### F-11 — Profile G method surface on all MCP++ services (gap-closure, 2026-10-14)
- **Intended:** every service answers the MCP++ Profile G (risk/scheduling) surface
  the desktop client and supervisor gateway consume.
- **Observed:** `mcp++/risk/profile` answers on all three adapters with the genuine
  per-owner profiles (kit: `RuntimeProfileG@1` from its own transport; datasets:
  canonical profile from `profile_g_service`; accelerate: the upstream's native
  profile, whose REST facade was repaired by F3). `goals/list`, `tasks/list`,
  `tasks/ready`, `schedule/frontier` return real pages on all three; a write
  (`goals/create {}`) reaches the accelerate backend's own validation. With the
  upstream killed, the adapter fails closed with `-32051 G_PROVIDER_UNAVAILABLE`
  (module test) — no fabricated profile. Warm dispatch latency ~0.0 s via the
  persistent worker bridge. **Verdict: PASS (contract map R1).**

### F-13 — Per-app MCP++ interaction design (sharpened-requirement audit, 2026-10-14)
- **Intended:** every tool_backed app is actually designed to interact with
  its backend over MCP++: controls resolve to real owner tools through the
  gateway mediator, declared transports really execute, rendered state is
  truthful, mutating controls are confirm-gated in the UI flow.
- **Observed:** per-app mediated invocations built exactly as the apps' own
  gateway panel builds them: **38/38 apps executed** over http (receipt +
  Event-DAG ref + persisted receipt + UCAN-verified observation each);
  **10/10 libp2p-declaring apps executed over libp2p** through the mediator
  (after the R5 bridge/helper fix — the path was dead before: bridges
  crashed on the missing canonical pymultihash shim); the other 28 apps
  are http-only by declaration. Unconsented-mutation probes **26/26
  denied `confirmation_required`** mediator-side; the panel itself can
  only ever rehearse governed controls (confirmation-gated dry run — the
  repo's own e2e pins this as the intended class), browser-verified with
  a governed click in vibecode. Truthfulness: matrix↔catalog zero
  mismatches for all 38; browser probe of 8 apps (all owners +
  non-tool-backed) — rendered control states match live truth, **0
  mismatches**; non-tool-backed apps mount no panel. **Verdict: PASS**
  (contract map P15 + R5). Evidence `fv_state/audit2/`,
  screenshot `fv-13-ui-truthfulness.png`.

### F-12 — Live libp2p host-to-host MCP++ session (gap-closure, 2026-10-14)
- **Intended:** two real libp2p hosts run an MCP++ session (descriptor + UCAN
  identity + a tool call) — the transport proof the peers surface alone could not
  give.
- **Observed:** two `MCPp2pNode` hosts (repos' Profile E code, pinned py-libp2p
  0.7.0) on loopback, both operational; descriptor exchanged (CID-addressed),
  UCAN-gated tool call authorized server-side by `DelegationEvaluator`,
  execution receipt CID issued, wrong-resource and missing-delegation calls
  refused. Same-machine two-host session — real transport, no mocks.
  **Verdict: PASS (contract map B4); evidence
  `fv_state/p2p-session-evidence.json`.**

### F-14 — Interaction coverage: every GUI interaction traces to a backend feature or a typed disposition (audit3, 2026-10-14)
- **Intended:** every user interaction in the GUI apps connects to some
  feature of the ORB/IDL of the MCP++ interface to one of the three backend
  services — especially the ipfs_accelerate_py agent supervisor — or carries
  an honest declared-local/external or typed disposition; no canned surface
  may present fabricated results as live.
- **Observed:** full control census (45 apps, 1,401 static controls) and a
  per-app trace table (`fv_state/audit3/trace-table.json`, `TRACE_TABLE.md`).
  Supervisor console: 9 of 15 capabilities execute live (the four audit3
  fix-3 mappings — logs, receipt persist/retrieve, DAG checkpoint — proved
  by a full gateway round-trip: persist `denied` without confirmation,
  then persisted/verified/retrieved under CID
  `bafkreidjbmeouqe42mu3uioynseoqgdtfjzrs3yiqv743jcxd56ftvpkw4` (helia),
  checkpoint event `bafkreicbw5f2hfeflzmtksufkqfzfwxhl6i25qyiu7ui2ujhwzm7a6trwy`);
  steering dry run's local preview restored (confirmed steering stays
  typed — no adapter route exists, contract map B10; **route built in
  the steering build, see F-15**); the settled
  console's only errors are the four capabilities with no backend feature
  (B8), and live mode renders zero SAMPLE fixtures (R6). The console's 8
  formerly-dead VDA-G054 buttons now navigate to the real panes (R8).
  datasets-browser and accelerate-panel — formerly canned despite being
  tool_backed — now invoke real descriptor operations and render the
  returned envelopes; every fabricated CID/receipt and the fake WebGPU
  completion claim are gone (R9, R10; accelerate Cancel is typed — the
  descriptor exposes no cancellation operation).
  **Verdict: PASS with typed exceptions (contract map P16; R6–R10 fixed;
  B8/B9/B10 typed).** Screenshots `fv-14…fv-17`; evidence
  `fv_state/audit3/`.

### F-15 — Confirmed prompt steering route (steering build, 2026-10-14)
- **Intended:** a confirmed steering submission in the Agent Supervisor
  console executes for real against the ipfs_accelerate_py agent
  supervisor — the facade's `Supervisor.steer` — through the MCP++
  interface, with the P11 governance contract intact (unconfirmed denied,
  dry run = local preview only, no simulated success).
- **Observed:** the route is built at the three layers the evidence
  supports and dispatch is proved live at every hop (contract map P17):
  gateway `invokeSupervisorPromptSteering` (dry run → typed
  `capability_unavailable`, so the console's R7 local preview engages —
  in-browser preview receipt `rcpt-prompt-steering-d0d1923a`; unconfirmed
  → `denied/confirmation_required` at the gateway; confirmed → RPC) →
  accelerate adapter method `agent_supervisor.prompt_steering.request` →
  persistent steering bridge worker hosting ONE production Supervisor
  session (opened live from the ipfs_accelerate repository, ASE3-026
  activation verified, composition CID
  `baguqeerauqzq7qsd5l23zxfasd7it6rhxabq747agtnelhkmqnbcgfg5tm3a`) →
  the backend's own `agent_supervisor_steer` prompt-lifecycle tool.
  **Terminal boundary (typed, B10):** the session's seed run cannot be
  created — originally because `Supervisor.run()` required
  `ipfs_datasets_py.logic.formalization.autoencoder.source_screening`,
  absent from the pinned datasets checkout (cross-repo pin skew); the
  backend's verbatim typed error surfaces through every hop
  (adapter probe, node gateway check, in-browser gateway + console path)
  as `server_unavailable`, never as a fabricated acceptance. The
  console's steering target list (Profile G snapshot) also remains
  empty: the seed artifact chain validates locally under the backend's
  own `GoalPlanValidator`, but this stack's Profile G services are
  constructed without authority/policy validators, so creates fail
  closed with `G_AUTHORITY_DENIED` by design.
  **Pin advance (2026-10-14):** the datasets pin was advanced
  (`external/ipfs_datasets` → `f4a823231ad52c9252504810a1b00ed4738346b6`);
  `source_screening` is present and importable from the pinned submodule,
  and on the restarted stack the seed run now proceeds into plan
  construction — the boundary moved to an ipfs_accelerate_py internal
  inconsistency (facade projects scope_paths `"."` for a root scan;
  `plan_revision_contracts` rejects `"."`: `PlanRevisionPathError`,
  typed in B10). Governance re-proved at the new pin at every hop
  (gateway check + Playwright drive: dry run → local preview receipt
  `rcpt-prompt-steering-7a6205d4`; unconfirmed → denied; confirmed →
  dispatched, `server_unavailable` with the new verbatim cause; adapter
  session snapshots before/after byte-identical — fail-closed).
  **Verdict: PASS for the route and its governance; execution remainder
  typed at B10 with the exact blocking piece named.** Screenshots
  `fv-18-supervisor-steering-live.png`, `fv-19-supervisor-console-live.png`;
  at the new pin `fv-20-supervisor-steering-newpin.png`,
  `fv-21-supervisor-steering-after-confirmed.png`,
  `fv-22-supervisor-console-newpin.png`;
  evidence `fv_state/steering_route/`, `fv_state/pin_advance/`.

  **Finisher (2026-10-14):** the two ipfs_accelerate_py inconsistencies
  in the run-creation chain are FIXED (uncommitted; contract map B10
  carries the evidence chain): the plan-scope projection now emits the
  contracts' empty-tuple unnarrowed scope for a root scan instead of
  leaking the scan layer's `"."` sentinel, and the facade supplies the
  scanner's canonical allowlist/repository-root identities when
  constructing the workflow request. Run creation now passes plan
  construction and both scanner identity checks and reaches the real
  directory scan, which terminates execution under its designed,
  test-pinned policy: `NestedRepositoryError: nested repository or
  submodule is forbidden at 'docs/fastmcp'` — ipfs_accelerate_py's HEAD
  contains 10 tracked submodules, and it is the only repository here
  with an activated production composition. Re-proved live on the
  restarted stack at every hop: adapter probes (two identical
  fail-closed sessions, composition CID unchanged), node gateway check
  PASSED (dry run → local preview; unconfirmed → denied; confirmed →
  `server_unavailable` with the verbatim cause), browser console path
  (dry run → local preview receipt `rcpt-prompt-steering-9eb1272c`;
  confirmed → the verbatim cause rendered). Suites: accelerate plan
  set 143 passed before/after (fully unsealed re-runs); facade set
  82 passed / 2 failed / 41 errors before/after (identical pre-existing
  failures); superproject integration 528 passed / 29 skipped /
  0 failed; steering vitest batch 17/17. **Verdict stands: PASS for the
  route and governance; the execution remainder is the backend's
  designed nested-repository policy — a deployment decision (a
  submodule-free supervisor target), not a defect.** Screenshots
  `fv-23-supervisor-steering-finisher.png`,
  `fv-24-supervisor-steering-finisher-after-confirmed.png`,
  `fv-25-supervisor-console-finisher.png`,
  `fv-26-supervisor-steering-finisher-confirmed.png`;
  evidence `fv_state/pin_advance/`.

### F-16 — Audit4 verification pass (2026-10-15)
- **Intended:** re-verify every suite baseline on the current tree (steering route + datasets pin
  f4a82323 + two accelerate seam fixes, all uncommitted); re-scan the GUI↔backend inventory for
  new controls and new fabricated claims; fix what the scan finds.
- **Observed:** datasets ui_ux_ir **361 passed / 1 failed** (the 1 = known B3 checkout-layout);
  solver determinism 1 passed; mcp_idl_identity_contract 32 passed; superproject integration
  **528 passed / 29 skipped / 0 failed**; steering vitest batch **17/17** (also after the fixes
  below); inventory re-run **45 apps / 1,401 controls — identical to audit3**, zero new controls;
  R-f/R-g fixes hold (fabricated CIDs/receipts gone from datasets-browser and accelerate-panel).
  Accelerate plan set **143 passed / 0 failed**; facade set **82 passed / 2 failed / 41 errors**
  (both failures + all errors pre-existing/environmental, identical to baseline). Fixes applied: stale "no steering route" comment corrected (R-h); steering result
  pane Mode badge now marks the standalone local preview honestly (R-i); 11 VDA evidence sections
  carry an explicit "Evidence draft — fixture references" marker (R-j; strudel already declared
  local). Steering confirmed-steering disposition moved out of typed-unavailable: the route is real
  end-to-end; live execution currently terminates at the backend's designed, test-pinned
  `NestedRepositoryError` policy — surfaced verbatim, fail-closed (a deployment decision, not a
  defect). The 6 remaining typed-unavailable capabilities re-verified as genuinely absent in the
  backends. All changes UNCOMMITTED.
- **Program state:** `~/workspace/goals/lift-coding-swissknife-gui-integration/hidden_files/audit4_*`
  (suite logs, scan census + notes).
- **Verdict: PASS — no regressions; 3 truthfulness gaps found and fixed.**

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
| `fv-14-supervisor-console-audit3.png` | Agent Supervisor console, audit3 cold-stack drive (no SAMPLE leakage; G054 navigation live) |
| `fv-15-datasets-browser-audit3.png` | datasets-browser after invoking all six operations (real gateway envelopes; no canned CIDs/receipts) |
| `fv-16-accelerate-panel-audit3.png` | accelerate-panel after invoking all five operations (real envelopes; no fake WebGPU claim) |
| `fv-17-supervisor-console-audit3-warm.png` | Agent Supervisor console settled on the warm stack: health available, error set = the four typed capabilities |
| `fv-18-supervisor-steering-live.png` | Agent Supervisor console, Steering pane on the live stack (steering build): planned MCP action `agent_supervisor.prompt_steering.request`, no target in the empty Profile G snapshot |
| `fv-19-supervisor-console-live.png` | Agent Supervisor console live state during the steering-route drive (health available, snapshot genuinely empty) |
