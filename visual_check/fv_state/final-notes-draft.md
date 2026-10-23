## Gap-closure pass — final summary (2026-10-14)

Benjamin's directive (2026-10-13 20:24 PDT): solve the gaps so all backends
work and fix all the broken contracts; source fixes authorized where a
contract is refuted. Everything below is an UNCOMMITTED change set — no
commits, no pushes. Baseline: superproject 8ce1bb13, swissknife cd37eeb4,
external/ipfs_accelerate 125a0b87f. The pre-modified datasets file
(processors/legal_scrapers/.../czechia.../normalize.py) was NOT touched.

### Changed files, grouped by fix

**R1 — Profile G on all three compat adapters (incl. enabling fix F3)**
- NEW swissknife/scripts/mcpplusplus-profile-g-adapter.cjs — canonical
  Profile G surface (all 23 methods + REST bindings mirrored from
  ipfs_datasets_py's profile_g_service), per-owner adapters, availability
  caching for risk/profile, fail-closed -32051 G_PROVIDER_UNAVAILABLE.
  Kit/datasets dispatch runs through a persistent Python worker bridge
  (JSON-lines stdio; imports the owner dispatcher once) — v1 (spawnSync)
  froze the event loop, v2 (per-call spawn) still cost seconds; warm
  dispatch is ~0.0 s with the worker.
- swissknife/scripts/start-ipfs-kit-mcp-compat.cjs — Profile G wiring
  (require, createKitProfileGAdapter, RPC branch, GET /mcp/risk/profile
  route, listen-time warm-up).
- swissknife/scripts/start-ipfs-datasets-mcp-compat.cjs — same five
  touches (createDatasetsProfileGAdapter over profile_g_service).
- swissknife/scripts/all-tools-evidence-lib.cjs — accelerate Profile G
  wiring (createHttpProfileGAdapter proxying the upstream's normative
  REST bindings) inside startAccelerateCompatServer.
- external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/fastapi_service.py
  (F3) — module-level guarded `from fastapi import Request`. Root cause:
  `from __future__ import annotations` + Request imported only inside
  create_fastapi_app() left the module-global annotation unresolved, so
  FastAPI treated `request` as a query parameter (422) / raised
  PydanticUserError (500) on the Profile G (and Profile D) REST facades.

**X1 — alias resolution in the served shell**
- swissknife/web/js/main-simple.js — VIRTUAL_DESKTOP_ALIAS_TO_ID mirror +
  resolveVirtualDesktopAppId mirror + launchApp resolves before lookup.

**Item 4 — supervisor console gateway**
- swissknife/web/js/main-simple.js — createAgentSupervisorApp installs
  the MCP++ desktop client's createSupervisorGateway() as
  window.agentSupervisorGateway when no gateway/endpoint is configured.

**R4 — solver determinism**
- external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/solver.py
  — SolverBoundsReceipt.to_dict() no longer serializes wall-clock
  elapsed_ms into the deterministic artifact digest input (comment added;
  attribute + live bound check untouched).

**B6 — JevOps (no repo files)**
- Cloned endomorphosis/JevOps (shallow) to ~/lift_coding/JevOps.

**B4 — libp2p (environment only)**
- Installed the repos' pinned py-libp2p (0.7.0 @ 20d9527f) + companions
  into ~/workspace/lift_coding/.venv. Session driver + evidence under
  visual_check/fv_state/ (p2p_session.py, p2p-session-evidence.json).

**Evidence/harness (visual_check/, uncommitted)**
- fv_state/{explorer_probe,alias_probe,console_probe}.mjs + *-results.json
- fv-11-explorer-healthy.png, fv-12-supervisor-console-live.png
- fv_state/{uiuxir-suite,full-collect,integration-gap-pass}.log
- fv_state/drive-results.json (gap-pass sweep; prior results preserved as
  drive-results-functional-pass.json)
- SVD-132 batch harness: scratch spec/config were created inside
  swissknife (test/e2e/zz-gap-svd-batch.spec.ts,
  build-tools/configs/zz-gap-svd-batch.config.ts) for the batched runs and
  DELETED afterwards; the master copies live at
  visual_check/fv_state/{svd132-batch.spec.ts,playwright.svd-batch.config.ts}.

### Verification numbers
- Explorer live: ready, "3/3 MCP++ services responded.", 461 tools.
- Console live: ready/degraded (not fallback); live queue/goals/receipts.
- Alias probe: 3/3 aliases open+close canonical windows; unknown id no-op.
- Drive sweep: 45/45 canonical apps open/focus/close (post-X1).
- ui_ux_ir suite: 285 passed / 1 failed (B3 only) — was 284/2.
- test_solver.py: 20/20 incl. test_solver_is_deterministic.
- Full collection (B6): 3,273 tests, 0 errors.
- Integration suite (closing): 528 passed / 29 skipped / 0 failed (223 s).
- libp2p session: connected; descriptor CID exchanged; UCAN-gated tool
  call authorized (receipt CID issued); 2/2 negative controls refused.

### Left typed (no fix faked)
- B1: <OUTCOME>
- B2: producers attempted standalone with the sealed toolchain; both die
  on their in-spec budgets (180 s / 420 s) on this 2-core VM under
  co-tenant load ~13-25 (SWR-096 attempt reached 23 screenshot
  attachments). SWR-096 still fails on the missing artifacts — an
  availability-of-evidence failure, not a product-behavior failure.
- B3: checkout-layout artifact; mechanism documented in the map.
- B4 remainder: sealed DCR service evidence (doc 48: sealed bootstrap on
  a dedicated clean integration branch; not generatable from this tree).
- B5: Leanstral is an external 119B-model server at 127.0.0.1:8080; the
  repo ships only the client adapter.
- B7: strudel CDNs refused by the egress proxy; the loader is CDN-first
  by design (npm fallback is a legacy webpack path).
