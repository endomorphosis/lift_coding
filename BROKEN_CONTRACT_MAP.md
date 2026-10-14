# Broken-Contract Map — SwissKnife ↔ MCP++ Interfaces

**Pass:** functional verification + formal contract mapping, 2026-10-13 (worker pass;
companion to `visual_check/FEATURE_MATRIX.md` and `SWISSKNIFE_FIX_NOTES.md`).
**Baseline:** superproject `22d7c782b`, swissknife `f2972b38`, `external/ipfs_accelerate`
`125a0b87f`, plus the prior pass's uncommitted verification change set. Nothing committed
by this pass.
**Method:** interface contracts from the ORB/IDL descriptors
(`src/services/mcp/*interop-descriptor.ts`, `src/services/glasses/desktop-orb-idl-contract.ts`),
the MCP-IDL manifests, and the MCP++ protocol surface were compiled into proof obligations
and discharged through `ipfs_datasets_py.logic` (Z3ProverBridge, TDFOL) where the contract
is finite-state, through the repos' own test/evidence routes where those are the contract's
home, and against **live program state** captured from the running stack (vite mediator
:3001, compat adapters kit :8014 / datasets :3002 / accelerate :3003, accelerate upstream
:9000, datasets dashboard :8899). Every functional failure in the feature matrix is
cross-referenced here, and every refuted contract was checked for a visible symptom.

**Totals:** 22 obligation groups — **14 proved, 3 refuted, 1 refuted-at-a-boundary
(recorded as a proved boundary contract with a refuted raw form), 4 blocked** (plus 3
standing known gates carried as typed dispositions). The 2 in-scope refutations that were
repairable as binding alignments were fixed (F1, F2) and re-verified.

---

## 1. Proved contracts

| # | Contract (source) | Obligation / check | Evidence |
|---|---|---|---|
| P1 | Live discovery parity — gateway controls resolve against owner `tools/list` (ALL_APP_LIVE_TOOL_BINDINGS ↔ MCP servers) | Z3, one obligation per owner: every control's `selected_tool_id` ∈ owner's live tool set; plus foreign-probe exclusion per owner | **PROVED ×6.** Live state: kit 124 tools, datasets 319, accelerate 18; 79/79 controls available. Driver `visual_check/fv_state/prove_contracts.py`, results `fv_state/proof-summary.json` |
| P2 | Binding completeness — every `tool_backed` app has ≥1 available control; every control names a manifest app | Z3 over the live backend-status matrix (45 apps) + bindings | **PROVED.** 38 tool_backed apps all covered |
| P3 | Confirmation coherence — every mutating control requires confirmation (doc 48 §9 transaction model) | Z3 over all 79 live controls | **PROVED.** No mutating control lacks `confirmation_required` |
| P4 | Backend-status coherence — status states ∈ declared set; every non-live status carries a reason; `denied` names a policy | Z3 over all 135 statuses | **PROVED.** 79 live / 3 denied (api-keys, `credential-isolation-v1`) / 32 unavailable (undeclared per-owner capability, reasoned) / 15 local-only / 6 external-provider |
| P5 | MCP++ receipt schemas (prior pass, carried at the committed baseline) | 25 Z3 obligations (admit-new / excluded-pre / backward-compat / strict-extension countermodels / foreign-excluded / genuine-receipt triple) | **PROVED 25/25** (prior pass, `SWISSKNIFE_FIX_NOTES.md` WS2; schemas unchanged since) |
| P6 | FormalClaimAlgebra (Mcp-Plus-Plus/formal/lean) | Lean kernel check | **PROVED 48/48**, zero `sorryAx` (prior pass, carried) |
| P7 | MCP-IDL identity — descriptors derive stable identities across the Python/TS boundary (datasets `ui_ux_ir` suite) | `tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py` (superproject forwarding) | **PROVED — 33 passed** (post-restore; was DELETION-BLOCKED in the prior pass's framing) |
| P8 | Cross-language golden vectors (ui_ux_ir ↔ TS) | swissknife vitest `ui-ux-ir-cross-language.test.ts` over restored `golden_vectors.json` | **PROVED — 4 passed** (post-restore) |
| P9 | ORB/IDL complete coverage (desktop-orb-idl-contract) | Regenerated `orb-idl-complete-coverage.json` + `desktop-orb-idl-contract.test.ts` + `glasses-manifest-coverage.test.ts` (SWR-006) | **PROVED.** 45 apps / 45 descriptors / 45 interface CIDs / 225 modalities / 225 typed fallbacks / 122 declared unsupported modalities / 34 confirmed-policy actions; supervisor projection read-only, `steering_requires_confirmation: true` |
| P10 | Mediated execution contract — browser → gateway `/mcp/tools/call` → policy → owner tool → CID receipt + Event-DAG entry (doc 48 §§4–5) | Live invocation from MCP Control: datasets `inspect_tool_registry` control | **PROVED live.** HTTP 200, outcome `executed`, Policy `allow`, receipt `bafkreigwbyyyhfizc2bzhudfn57amu2mmkqmoichjjafwckf4mridq2nry`, event `bafkreibo4xqigvcy45zykwawur4uz3qktfi2hk2u74orou7b3k3x6yinxu`, tool result = real category catalog |
| P11 | Governed steering confirmation contract (supervisor ↔ MCP++, ORB coverage `steering_requires_confirmation`) | Live exercise in the Agent Supervisor console | **PROVED live, both directions.** Unconfirmed submit → policy denial with recovery text on all 3 owner rows; dry-run + confirmed submit → normalized plan (target `task:SWR-105-1`, policy class `confirm`), correlation id, receipt `rcpt-prompt-steer…` |
| P12 | MCP++ inspection method surface (desktop client ↔ each service): `initialize`, `tools/list`, `interfaces/list`, `mcp++/dag/frontier`, `mcp++/p2p/peers`, `/mcp/health`, `/mcp/helia/status` | Live JSON-RPC probes per adapter + in-browser capture | **PROVED** for all listed methods on all 3 adapters; `mcp++/p2p/peers` returns protocol `/mcp+p2p/1.0.0`; Explorer discovered 461 tools (124+319+18) with capability tags negotiated |
| P13 | Datasets generic dispatch contract (datasets adapter → datasets dashboard execute endpoint :8899) | Explorer explicit call `tools_list_categories` | **PROVED with the full stack.** Without the dashboard: `isError` receipt (`fetch failed` to `127.0.0.1:8899`, by-design error surfacing). With `ipfs_datasets_py.dashboards.launch_mcp_dashboard` running: `isError: false`, HTTP 200, real result. The dashboard is a required stack component (adapter env `IPFS_DATASETS_DASHBOARD_URL`, default :8899) |
| P14 | ORB/IDL-adjacent evidence suites | `mobile-orb-edge-all-apps.test.ts`, `agent-supervisor-console-evidence.test.ts`, `meta-glasses-simulator-handoff-evidence.test.ts` (SWR-097) | **PROVED** (SWR-097 after regenerating `glasses-simulator-handoff.json` via its own builder; the artifact's absence was a prereq-chain artifact, see B2) |

## 2. Refuted contracts

| # | Contract | Counterexample (live) | Functional symptom | Disposition |
|---|---|---|---|---|
| R1 | Every MCP++ service answers the desktop client's inspection method `mcp++/risk/profile` (called by `web/js/core/mcp-plus-plus-desktop-client.js` on every service) | All three compat adapters return `{"code":-32601,"message":"Unsupported method mcp++/risk/profile"}` (direct JSON-RPC probes + in-browser capture). The accelerate *upstream* implements `/mcp/risk/profile` natively; the adapters do not expose the method | MCP++ Explorer reports **DEGRADED — "2/3 MCP++ services responded"** despite complete tool discovery (461 tools) | **REFUTED, not fixed.** Implementing a protocol method inside the adapters is source implementation, outside the descriptor/registration/binding/schema-alignment fix scope of this pass. Owner: swissknife compat adapters (`scripts/start-ipfs-*-mcp-compat.cjs`) |
| R2 | SVD-132 Playwright driver ↔ served desktop interface: the driver assumed `desktop.closeWindow(el)` exists on the served shell | Runtime probe of the served desktop (`web/index.html` → `web/js/main-simple.js`): `SwissKnifeDesktop` prototype + own properties contain **no** `closeWindow` (the full `web/js/main.js` defines it at line 2261 but is not the served entry). The audit's own evidence file records the counterexample per app: `close_reopen.error: "page.evaluate: TypeError: desktop.closeWindow is not a function"` (`svd-132-playwright.json`, run of 2026-10-13T23:35Z; all 48 apps failed, 0 passed) | The SVD-132 real-browser audit could never record a successful close/reopen for any app against the served shell (user-facing impact: none — the shell's own titlebar control closes windows correctly) | **REFUTED → FIXED (F2).** Driver `closeApp` now clicks the window's `.window-control.close` control (the shell's real close path — the same click its in-window Close buttons dispatch) and verifies removal from `desktop.windows`. Verified: the lean drive closes 45/45 windows via this path |
| R3 | SVD-132 Playwright driver module interface: driver imported `resolveVirtualDesktopAppId` from the audit runner | `SyntaxError: The requested module './virtual-desktop-app-audit-runner.js' does not provide an export named 'resolveVirtualDesktopAppId'` — the symbol lives in `virtual-desktop-app-manifest.ts` (line 1132); the runner imports but never re-exports it | The SVD-132 audit failed to load at all ("No tests found") | **REFUTED → FIXED (F1).** Driver now imports the resolver from `./virtual-desktop-app-manifest.js`, its canonical module. Verified: audit loads and executes (subsequently budget-blocked, B1) |
| R4 | `ipfs_datasets_py` ui_ux_ir projection solver determinism (`tests/unit/logic/ui_ux_ir/projection/test_solver.py::test_solver_is_deterministic`) | Two solver runs in one process produce different digests: `sha256:cc71ca45…` vs `sha256:9d596c68…` (post-restore suite run: 284 passed / 2 failed) | None in the desktop: no SwissKnife surface consumes solver-digest equality at runtime. The failure is internal to the datasets logic platform | **REFUTED, not fixed.** Owner: ipfs_datasets_py projection solver; a fix would be source synthesis in the solver, outside this pass's interfacing scope |

### Boundary case (proved with a refuted raw form)

| # | Contract | Finding |
|---|---|---|
| X1 | Manifest alias ids are launchable (48 ids = 45 canonical + `code-editor`, `strudel-grandma`, `p2p-chat-offline`) | **Resolver-mediated form PROVED:** `resolveVirtualDesktopAppId` maps each alias to its canonical app (manifest test) and the audit driver resolves before launching; all 3 canonical targets open. **Raw form REFUTED:** `desktop.launchApp('code-editor')` → console `App code-editor not found` (same for the other two aliases) — the served desktop's `launchApp` does not itself resolve aliases. Recorded as a desktop-shell divergence with a working documented caller contract; no fix attempted (changing `launchApp` semantics is a product source change, not an alignment) |

## 3. Blocked (typed dispositions — no pass claimed)

| # | Item | Exact blocker |
|---|---|---|
| B1 | SVD-132 real-browser audit (`test:e2e:app-audit-runner`), post-F1/F2 | **BLOCKED-BY-RUNTIME-BUDGET.** The post-F1 run exceeded the test's own 900 s Playwright budget (~35–50 s/app: dual-viewport deterministic-PNG screenshots + close/reopen cycles against a cold vite dev server on this VM); a warm-cache retry paced identically and was stopped at the same frontier. The run's evidence file **was** written (`svd-132-playwright.json`, generated 2026-10-13T23:35Z): 48 apps recorded, **0 passed / 48 failed, 26 of 96 screenshots captured** — every app's close failed on the R2 `closeWindow` TypeError (pre-F2 driver), and the back ~34 apps' records are contaminated by the timeout teardown ("Target page, context or browser has been closed"). 18 apps' complete screenshot sets are retained under `test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots/svd-132-playwright/`. A post-F2 full-budget completion was not obtained on this VM. Functionally superseded by the lean drive (45/45 apps, `visual_check/FEATURE_MATRIX.md`) |
| B2 | SWR-096 virtual-desktop tool-UI smoke evidence test | **BLOCKED-BY-RUNTIME-BUDGET (evidence generation).** Its producer tests (HAO-704 `mcp-dashboard.spec.ts`: "opens every tool-backed virtual desktop app" — 180 s timeout; "generates exhaustive SWR-102 workflow matrix" — 420 s timeout) both timed out on this VM, so `tool-ui-smoke-receipts.json` and `app-workflow-matrix.json` were never generated and SWR-096 fails on the missing artifacts. Every other prereq in the chain was regenerated by running its builder directly (each exits 0 standalone; the chained runner races its own adapter restarts — ledger and live-probe captures each failed inside the chain, passed standalone). Live-probe capture standalone result: 69 live dispatch receipts, 246 policy-gated evidence items, `libp2p_decision: go` |
| B3 | Datasets `test_domain_slice.py::test_ui_ux_adapter_note_declares_required_contract_fields` | **BLOCKED-BY-CHECKOUT-LAYOUT.** The test searches ancestors of its own file for `data/agent_supervisor/logic_platform_canonicalization/notes/intent_uiux_adapters.md`; in the submodule layout the note lives in the *sibling* `external/ipfs_accelerate/data/…`, unreachable by ancestor search (fallback resolves to nonexistent `external/data/…`). Content verified directly at the sibling path: the note declares all required fields (source domain, view, family / profile, property, notation, preserved semantics, lost semantics, assumptions, unsupported constructs, proof-safety, counterexample-safety, ui_ux_ir, declaration-only). Not a contract break |
| B4 | DCR live conformance (doc 48) | **Known gate, narrowed.** The historical `@ucans/ucans` blocker is *resolved*: package installed (`^0.11.4`, `node_modules/@ucans/{core,default-plugins,ucans}` present), Profile C module loads, and the gateway's UCAN verification path executed during live mediated calls (P10). Still blocked on **absent sealed service evidence**; a live libp2p host-to-host session was not driven this pass (peers surface answers with protocol `/mcp+p2p/1.0.0` and empty peer lists — no second host exists in this environment) |
| B5 | Leanstral codebase-proof scheduler route | **Known gate.** Provider endpoint `127.0.0.1:8080` down (health unreachable). The local-elan Lean route (P6) is the substitute discharge |
| B6 | `make test` (superproject) | **Known gate.** Collection requires a sibling JevOps checkout at `~/lift_coding/JevOps`. Superseded for this pass by direct pytest runs (unit forwarding suites + `tests/integration`) |
| B7 | Strudel audio engine init (`strudel`, `strudel-ai-daw`, `music-studio*`) | **BLOCKED-BY-EGRESS.** The apps load `@strudel.cycles` from `https://esm.sh` — the VM's egress proxy refuses the tunnel (`ERR_TUNNEL_CONNECTION_FAILED`); `strudel-ai-daw`'s launch promise therefore never settles (its window registers and closes normally). Same class: the desktop's unsplash wallpaper fetch fails (cosmetic). No repo contract is implicated |

## 4. Cross-reference: functional failures ↔ contract breaks

- Explorer **DEGRADED / "2/3 responded"** ↔ **R1** (risk/profile) — a refuted contract with a visible symptom. ✔ matched
- Explorer explicit call failure (first attempt) ↔ **P13** — not a break: an incomplete stack on my side (dashboard not launched); proved after launching the repo's own dashboard. ✔ matched, resolved by stack completion
- SVD-132 audit "No tests found", then timeout ↔ **R3** (fixed), **R2** (fixed), **B1** (budget). ✔ matched
- SWR-096 failure ↔ **B2** (evidence-generation budget), not a product contract. ✔ matched
- Alias launches failing from the raw desktop API ↔ **X1**. ✔ matched
- `strudel-ai-daw` launch-promise hang ↔ **B7** (egress), not an app defect — its window lifecycle is clean. ✔ matched
- Supervisor header **STATUS degraded / MODE fallback** ↔ no contract break: the supervisor's own console-gateway backend was not part of the launched stack; the app runs its designed browser-safe fallback with full local goals/queue/receipt state, and its MCP++ bindings + steering contract (P11) verify live against the mediator. Recorded as an environment-scope note, not a refutation.
- MCP Control "0 host daemons / 0 remotes" ↔ no break: true state of an unconfigured profile; its gateway bindings verify live (P10).
- **No functional failure lacks a contract-map entry, and no refuted contract lacks a checked symptom** (R4's symptom check is negative by inspection: no desktop surface consumes the solver digest).

## 5. Fixes applied (separate uncommitted change set)

| Fix | File | Change |
|---|---|---|
| F1 | `swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver.ts` | Import `resolveVirtualDesktopAppId` from `./virtual-desktop-app-manifest.js` (canonical module) instead of the audit runner, which does not re-export it |
| F2 | `swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver.ts` | `closeApp` closes via the window's `.window-control.close` titlebar control (the served shell's actual close path) and verifies the window left `desktop.windows` |

Both are binding alignments in the SVD-132 audit tooling; no product behavior, tests, or
schemas were changed or weakened. Re-verification: the audit loads and executes post-F1;
45/45 window closes succeed via the F2 path in the lean drive; the graded (simulated-driver)
manifest path is unaffected (it never imports the Playwright driver).

## 6. Suite re-runs after fixes

- `python -m pytest tests/integration -q` — **528 passed / 29 skipped / 0 failed**
  (421.9 s). Baseline 526 / 31 / 0; the +2 passed / −2 skipped delta is the restored
  `external/ipfs_datasets` tree un-blocking two previously skipped ui_ux_ir tests —
  not an effect of F1/F2 (TypeScript tooling, outside the Python suite's scope).
- Datasets `tests/unit/logic/ui_ux_ir/` (post-restore, read-only run): **284 passed /
  2 failed** → R4 + B3 above.
- Glasses/ORB-IDL vitest batch: 5 of 6 files pass (SWR-006, desktop-orb-idl-contract,
  mobile-orb-edge-all-apps, agent-supervisor-console-evidence, SWR-097); SWR-096 blocked (B2).
- Live-state Z3 obligations (this pass): **9/9 proved** (P1–P4 families).

*Environment note: the VM rebooted three times during this pass; all state was kept
under `visual_check/fv_state/` (bring-up script, captured program state, proof driver,
drive harness + per-app JSONL) and every figure above comes from files on disk or from
command output re-read after the fact.*
