# Swissknife ↔ MCP++ GUI fix — working notes

## Step 1: repo state (2026-10-13)
- Repo: ~/workspace/lift_coding, branch `main`, local HEAD `f2c7edcb1` ("Point the datasets and accelerate submodules at the published autoformal mains.").
- `git fetch origin main` succeeded (slow egress, ~90 s); `git rev-list --left-right --count HEAD...origin/main` = `0 0` → local main already identical to origin/main; `git pull` is a no-op. Nothing to update at superproject level.
- Pre-existing dirty state (NOT clobbered): `.handsfree_transport_sessions.json` (runtime session file), and submodule pointers `external/ipfs_accelerate`, `external/ipfs_datasets`, `external/ipfs_kit` show modified vs recorded SHAs (per-submodule detail below).
- 8 submodules per .gitmodules: external/ipfs_datasets (branch agent/ui-ux-ir), external/ipfs_kit (main), external/ipfs_accelerate (main), external/meta-wearables-dat-android (main), external/meta-wearables-dat-ios (main), swissknife (agent/ui-ux-ir), Mcp-Plus-Plus (main), hallucinate_app (agent/ui-ux-ir).
- Swissknife is itself a submodule (github.com/endomorphosis/swissknife) — a TS/Vite app. Mcp-Plus-Plus is also a submodule in-repo.
- ALL 8 submodules verified checked out exactly at the superproject-recorded SHAs (recorded == current for every one). `git submodule update --init` (top level only) ran clean, exit 0.
- Found + repaired: the working trees of external/ipfs_datasets and external/ipfs_kit had been EMPTIED before this session (all files deleted; ~20,491 staged deletions in the datasets index — legacy of the earlier disk-blowup cleanup). Restored both from their local HEAD object stores (`git restore --source=HEAD --staged --worktree .`, then a staged-only pass); both now report clean `git status` (0 entries) and full file trees on disk (datasets: 10,033 files). ipfs_accelerate was already fully present/clean.
- Cyclic trio handling: the nested ipfs_(accelerate|datasets|kit) submodules INSIDE the submodule repos were deliberately NOT initialized (the cycle). Only the 8 top-level submodules were initialized, per the bounded procedure.
- Superproject still shows pre-existing modification of `.handsfree_transport_sessions.json` (runtime state file) — left untouched.
- Git is SLOW here (fetch ~90 s, restores 40–100 s); every command run under `timeout` with GIT_TERMINAL_PROMPT=0 as instructed; no hangs fatal.

## Diagnosis (written before code changes, 2026-10-13)

Executable contracts = `tests/integration/` in lift_coding (the docs' stated validation targets). Baseline run of the Swissknife interop + MCP++ suites: **6 failures** in 3 clusters; everything else passed (incl. desktop-app integrations, kit interop, MCP++ connector, Profile A–D cross-server interop).

1. **MCP++ compatibility-receipt schema lost the MCP++ identity** (`swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`). Later repairs for other surfaces overwrote its enums: `task_id.enum = ["HAO-445","MGW-574"]`, `daemon_id.enum` has no `mcp_plus_plus`, `server_package.enum` has no `Mcp-Plus-Plus`. A genuine SwissKnife→Mcp-Plus-Plus receipt (task VAI-665 / daemon mcp_plus_plus / package Mcp-Plus-Plus, per docs/integration/swissknife-mcp_plus_plus.md) can no longer validate. Failing: `test_swissknife_mcp_plus_plus_interop.py::test_swissknife_mcp_plus_plus_compatibility_receipt_validates`. Fix: extend the three enums additively (other consumers assert membership, never exact equality — verified by grep).

2. **Datasets Bucket-VFS descriptor binds phantom paths** (`swissknife/src/services/mcp/ipfs-datasets-bucket-vfs-interop-descriptor.ts`). Its four descriptor refs point at `external/ipfs_datasets/.tools/ipfs_kit_py/...`, a nested vendored copy that does NOT exist in this checkout. The real files live in the top-level submodule `external/ipfs_kit/{data/deprecations_report.schema.json, docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, examples/demo_bucket_vfs_interfaces.py, examples/demo_unified_bucket_interface.py}` (all verified present), and the Python handoff module `src/handsfree/swissknife_ipfs_datasets_interop.py` already resolves against `external/ipfs_kit/...`. Failing: `test_swissknife_external_ipfs_datasets_interop.py::test_swissknife_descriptor_module_exports_interop_contract`. Fix: repoint the TS descriptor's refs (+ header comment) to the canonical `external/ipfs_kit/...` paths.
   Related: the shared contract schemas' `$comment` lineage strings (control_surface_contract, interaction_envelope, mediation_receipt) are missing the MGW-571 entry, failing `test_..._control_surface_and_interaction_envelope_validate_for_ipfs_datasets`. Fix: append the MGW-571 lineage entry (same format as the existing MGW-574 entry) to all three `$comment`s.

3. **ipfs_accelerate MCP++ P2P transport breaks standalone/vendored loading** (`external/ipfs_accelerate/ipfs_accelerate_py/mcplusplus_module/p2p_transport.py`). The module family's convention is relative imports (the cross-repo test loader loads these modules under a synthetic `_acc_mcppp` package precisely to avoid sys.path conflicts, and sibling modules use `from .cid_ucan import ...`). `p2p_transport.py` alone uses absolute self-imports (`from ipfs_accelerate_py.mcplusplus_module.p2p.libp2p_runtime import ...` and `...leanstral_topology import ...`), which raise ModuleNotFoundError in that loading mode — so the Profile E wire surface (P2PMessage, MCP_P2P_PROTOCOL) is unreachable and cross-repo wire compatibility with ipfs_datasets_py's transport can't even be exercised. Failing: `test_cross_server_mcppp.py::TestProfileEInterop::{test_accelerate_p2p_message_format, test_cross_repo_wire_compatibility, test_protocol_id_matches}`. Contributing factor: `mcplusplus_module/p2p/__init__.py` line 8 does an UNGUARDED `from .. import _missing_dependency_stub` (everything else in that file is try/except-guarded), so importing `.p2p.libp2p_runtime` under a parent package that doesn't define the stub also dies. Fix: relative-first imports with absolute fallback in p2p_transport.py (the try/except convention already used by mcplusplus_module/__init__.py), and guard the p2p/__init__.py stub import with a local fallback definition.

Note on "GUI": in this codebase the Swissknife GUI/virtual-desktop surfaces consume exactly these MCP++ interface descriptors, control-surface contracts, and receipts (src/services/mcp/*, src/services/apps/*); the integration tests above are the executable contract for that interfacing, and the ipfs_accelerate_py `mcplusplus_module` + `agent_supervisor` packages and ipfs_datasets_py's `mcp_server` transports are the runtime side.

## Changes (all in working trees; nothing committed or pushed)

Superproject (lift_coding):
- `mobile/src/orb/metaGlassesOrbDescriptors.js` — added the missing `active_*` validation lineage (active_task_id HAO-730, active_attempt 2, active_task_board, active_objective_gap_ref, active_validation_confirmation_ref, active_validation_repair_ref) to the mobile interop descriptor.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` — appended the HAO-730 attempt-2 repair lineage bullet.
- `data/hallucinate_multimodal_control/discovery/2026-07-09-hao-730-attempt-2-objective-validation-repair.md` — appended VAI-661 attempt-1 cross-reference.
- `docs/integration/swissknife-external_ipfs_datasets.md` — corrected the four descriptor paths from the phantom `.tools` location to `external/ipfs_kit/...`.
- `SWISSKNIFE_FIX_NOTES.md` — this file.

swissknife submodule:
- `contracts/mcp_plus_plus_compatibility_receipt.schema.json` — enums extended additively: task_id += VAI-665, MGW-573, HAO-736; daemon_id += mcp_plus_plus, meta-wearables-dat-ios; server_package += Mcp-Plus-Plus, meta_wearables_dat_ios.
- `contracts/mediation_receipt.schema.json` — appended MGW-571 lineage entry to `$comment`.
- `contracts/control_surface_contract.schema.json`, `contracts/interaction_envelope.schema.json` — appended VAI-661 attempt-1 + HAO-730 attempt-2 lineage entries (with agent_identity/allowed_surfaces/arguments_hash norm terms) to `$comment`.
- `src/services/mcp/ipfs-datasets-bucket-vfs-interop-descriptor.ts` — four descriptor refs + header comment repointed from `external/ipfs_datasets/.tools/ipfs_kit_py/...` (nonexistent) to canonical `external/ipfs_kit/...`.
- `src/services/mcp/meta-wearables-dat-ios-display-interop-descriptor.ts` — appended the missing `buildSwissKnifeMetaWearablesDATIOSMCPPlusPlusCompatibilityReceipt()` builder, mirroring the Android descriptor's builder and the HAO-736 receipt payload.

external/ipfs_accelerate submodule:
- `ipfs_accelerate_py/mcplusplus_module/p2p_transport.py` — absolute self-imports converted to relative-first with absolute fallback (family convention).
- `ipfs_accelerate_py/mcplusplus_module/p2p/__init__.py` — guarded the `_missing_dependency_stub` import (canonical source `mcp_server.compatibility`, with a local mirror as last resort).

## Verification
- Baseline (pre-fix): 6 failures across test_swissknife_mcp_plus_plus_interop.py, test_swissknife_external_ipfs_datasets_interop.py, test_cross_server_mcppp.py (Profile E); 5 more pre-existing failures found in the neighboring mobile/iOS interop files (same defect family; the receipt-enum ones proven pre-existing via `git show HEAD:` — HEAD enum was exactly ["HAO-445","MGW-574"]).
- Post-fix targeted runs: all previously failing files pass (mcp_plus_plus 34 tests with cross-server + datasets files; iOS 7/7; mobile 5/5; datasets 7/7 after doc edit).
- FULL suite, docs' stated supervisor target `python -m pytest tests/integration -q`: **526 passed, 31 skipped, 0 failed** (24m36s, run against the final tree).
- Runtime proof beyond static contracts: via normal package imports (external/ipfs_accelerate + external/ipfs_datasets on sys.path), `MCP_P2P_PROTOCOL` matches across repos (`/mcp+p2p/1.0.0`), the `p2p` package imports through the repaired stub guard, and P2PMessage wire round-trips succeed in BOTH directions (datasets-encoded → accelerate-decoded and vice versa). No mocks; the real transports were exercised at message level. (A live libp2p host-to-host session was not exercised; test_p2p_transport_live.py inside the accelerate repo is the heavyweight suite for that and its collection alone exceeded a 200 s bound in this loaded environment.)
- TS: no tsc/tsx toolchain is installed for swissknife (no node_modules there); both edited TS descriptors parse cleanly via Node 24 type-stripping + vm.SourceTextModule, same as the unedited Android control file. Full swissknife `tsc` typecheck remains unexercised.
- The pre-existing full-`make test` JevOps collection blocker was not chased, per instructions.

## Verification pass (2026-10-13, later session — supervisor IR mapping + theorem prover + visual check)

Scope: Benjamin required (a) supervisor-driven mapping of intent_ir / codebase_ir / ui_ux_ir,
(b) theorem-prover discharge of the interfacing obligations, (c) visual check of the apps.
Environment note: the VM restarted mid-session (~21:18 UTC); workspace persisted, background
processes and /tmp logs did not. An earlier same-day claim that npm ci had finished was wrong —
fresh checks showed a partial install (1,177 pkgs, no .bin); npm ci was re-run.

### WS2 — theorem prover (completed first; evidence below)
- Solver provisioning: no z3/cvc5/lean/lake existed anywhere on the box (full-filesystem find
  empty; both Leanstral endpoints 127.0.0.1:8080 and 172.17.0.1:8080 return 000). Installed the
  repo-pinned solver into the venv: z3-solver 4.13.4 (matches the machinery's `solver:z3@4.13`
  identity). `logic/backends` also has lean/coq/isabelle/agda/tlaplus adapters — binaries absent.
- Supervisor's own probe (`agent_supervisor.proof.solver_readiness.probe_solver_readiness`):
  z3 family = supported / `reconstruction_ready`; dcec, tdfol, cec, hammer = unsupported
  (`backend_unavailable`) in this environment.
- Discharge: 25 obligations extracted mechanically from the real receipt schemas (git HEAD =
  pre-fix, worktree = post-fix), encoded in TDFOL (finite enumerated sorts: coverage +
  disjointness + identity axioms + a foreign probe value) and discharged through the repo's own
  `ipfs_datasets_py.logic` Z3ProverBridge (TDFOL→Z3). Result: 25/25 as expected —
  7 ADMIT-NEW proved, 7 EXCLUDED-PRE proved, 3 BACKWARD-COMPAT (∀x AdmOld→AdmNew) proved,
  3 STRICT-EXTENSION refuted with countermodels (the newly admitted values), 3 FOREIGN-EXCLUDED
  proved, GENUINE-RECEIPT triple (VAI-665 ∧ mcp_plus_plus ∧ Mcp-Plus-Plus) proved admitted
  post-fix and proved inadmissible pre-fix. Driver: /tmp/ws2_prove.py (scratch).
- Codebase-proof scheduler route (config/agent_supervisor_codebase_proof_scheduler.json):
  provider `leanstral-local` at 127.0.0.1:8080 is DOWN (health 000) → that route unavailable.
- Lean route: Mcp-Plus-Plus/formal/lean (FormalClaimAlgebra, lakefile pins Lean 4.33.0, no
  package requires). elan installed from the GitHub release tarball after
  raw.githubusercontent.com hung >20 min; toolchain leanprover/lean4:v4.33.0 download started
  from releases.lean-lang.org — build result pending (see below).

### WS1 — supervisor IR mapping (partial)
- gui-opt CLI (agent_supervisor.gui_optimizer.cli): `scan agent-supervisor` and
  `baseline agent-supervisor` both exit 0, target resolved, source
  swissknife/web/js/apps/agent-supervisor.js present (digest sha256:e677e439…).
  The Python CLI only PLANS the TypeScript bridge (executed:false); the semantic work is in
  swissknife/src/services/gui-optimizer/cli.ts — TS-side run pending node_modules.
- Board validators: DCR board (doc 48) valid:false — 10 errors, all bootstrap/source-binding
  (planning revisions not ancestors of current gitlinks; accelerator branch mismatch; 5
  bootstrap test files flagged unsafe vs the seal) — matches doc 48's own statement that the
  shared checkout fails preflight; no error touches the Swissknife↔MCP++ contracts.
  Formal-assurance board (doc 49 FACP): valid:true (61 tasks, 0 warnings).
  Verified-GUI-optimizer board: valid:false on 4 environmental errors only — sealed toolchain
  pin (wants Node v22.19.0/npm 10.8.2 exactly; host has 24.20.0/10.9.4) + .bin/playwright and
  .bin/vitest missing while npm ci was incomplete; re-check after install with the
  npx-provisioned pinned toolchain.
- Mapping gap #1: there is NO module named `codebase_ir` in either logic tree (grep = 0 hits).
  The codebase-side IR role is filled by ipfs_datasets_py.logic.ir_core + the supervisor's SCA
  structural IR / DCR normalized contract graph + semantic_state symbol graph.
  intent_ir ✓ (logic/intent_ir: models/compiler/contracts/api/service) and
  ui_ux_ir ✓ (logic/ui_ux_ir: models/canonicalize/conformance/decoder/projection/rendering/
  wire/receipts + swissknife codec/renderer) exist as named packages.
- Mapping gap #2: the superproject IR test tests/unit/logic/ui_ux_ir/
  test_mcp_idl_identity_contract.py SKIPS — the datasets suite it forwards to
  (external/ipfs_datasets/tests/unit/logic/ui_ux_ir/…) is absent at the pinned datasets
  checkout (721773d27 has no tests/ tree at all). Consistent with doc 49's note that the
  datasets ui_ux_ir work is untracked/excluded at the reviewed commit.
- VGO status script: board idle (no master running) — health snapshot only.

## Remaining open
- Changes are uncommitted in the three working trees (superproject, swissknife, external/ipfs_accelerate) — committing (incl. submodule pointer bumps) is a separate step whenever Benjamin wants it; nothing was pushed.
- Pre-existing `.handsfree_transport_sessions.json` modification in the superproject — untouched.
- Nested submodules inside the submodule repos (the cyclic ipfs trio) deliberately not initialized.
- ipfs_accelerate's internal mcplusplus_module test files (test_p2p_transport_discovery.py etc.) could not be run to completion here — collection/import alone exceeded 200 s under this VM's load; the cross-repo integration suite covers the same transport surface and is green.

## Verification pass — completion addendum (2026-10-13, later session)

Environment note: the VM restarted several times during this pass (one
restart killed the first `npm ci` at 1,177 packages and an integration-suite
run at 51%). Everything below is from fresh post-restart checks; an injected
"npm ci complete, 3,015 packages" handoff during the pass was false against
disk state and was disregarded. `npm ci` in swissknife was re-run to
completion (node_modules/.bin populated: vitest, vite, tsx, tsc,
playwright). Playwright's Chromium headless shell build 1187 was installed
(`npx playwright install --only-shell chromium`); the preinstalled
/opt/meta-chromium build rejects loopback navigation
(ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS) and was not usable for
screenshots.

### WS2 — theorem prover, completed
- Lean route COMPLETE: elan v4.1.2 installed from the GitHub release tarball
  (the elan-init.sh fetch hung; tarball route worked), toolchain
  leanprover/lean4:v4.33.0 installed (the version Mcp-Plus-Plus/formal/lean's
  lakefile.toml pins). `lake build` in Mcp-Plus-Plus/formal/lean: exit 0.
  Promotion.lean (not part of the lakefile's lib roots) elaborated directly
  via `lake env lean FormalClaimAlgebra/Promotion.lean`: exit 0, no errors —
  all 48 FormalClaimAlgebra theorems kernel-checked. Axiom sweep on a
  scratch copy (repo files untouched): 48/48 theorems report dependencies,
  ZERO sorryAx; 9 depend only on [propext], the rest additionally on their
  per-theorem native_decide axioms (decidable finite checks, standard trust
  basis). Build byproducts (.lake/, lake-manifest.json) are untracked in
  the Mcp-Plus-Plus tree; no tracked file modified.
- Accelerate proof-machinery suites (test_agent_supervisor_code_contract_
  prover / code_proof_obligation_cache_keys / code_proof_context /
  code_proof_reproof / code_proof_scopes / code_proof_query): 204 passed,
  28 skipped, 1 failed — the one failure is collection of
  test_supervisor_mcp_server.py hitting the known JevOps sibling-checkout
  blocker (ModuleNotFoundError: jevops; ~/lift_coding/JevOps does not
  exist), not a proof failure. All code-proof assertions passed with the
  provisioned z3 (machinery binds solver:z3@4.13; z3-solver==4.13.4 pip-
  installed into the venv). Note: the verification executor's default proof
  argv is /usr/bin/z3 (absolute) which does not exist here; name-based
  probes find the venv z3 — recorded as an environment distinction, not a
  defect in the interfacing surface.
- (SMT discharge of the 25 receipt-schema obligations via the datasets
  Z3ProverBridge — 25/25 as expected — is recorded in the WS2 section above
  and stands.)

### WS1 — TS-side checks run; three defects found and FIXED
Focused Vitest batch after npm ci (build-tools/configs/vitest.config.ts):
initially 47 passed / 3 failed —
1. test/mcp-plus-plus/ui-ux-ir-cross-language.test.ts could not run:
   golden_vectors.json missing at
   external/ipfs_datasets/tests/fixtures/ui_ux_ir/v1/ — same root cause as
   mapping gap #2 (the pinned datasets checkout has no tests/ tree).
   Environmental/pin gap; fixtures were NOT fabricated. Still open.
2. test/mcp-plus-plus/mcp-dashboard-browser-policy.test.ts: doc 49's known
   pre-existing failure — the test expected the disclaimer to contain
   "in-browser Python runtime" while the source constant
   MCP_DASHBOARD_PYTHON_HOST_DAEMON_DISCLAIMER says "in-browser Python code
   interpreter" (the same test already treats the constant as truth via an
   equality assertion). FIXED test-side: expected substring updated to the
   constant's wording. Source untouched.
3. test/unit/services/gui-optimizer/agent-supervisor-baseline.test.ts (2
   tests): the computed semantic baseline no longer contains
   'missing-field-error-association' and no longer equals the committed
   evidence, because the live app source (web/js/apps/agent-supervisor.js)
   HAS since gained real field-to-error association (helper emitting
   aria-invalid/aria-describedby/aria-errormessage; submit controls wired
   with aria-describedby to the steering/dispatch error ids — verified in
   source and live, see WS3). The analyzer therefore correctly stopped
   flagging it; the committed evidence + test expectation were stale at
   HEAD (working tree had not touched app source, target, test, or
   evidence). FIXED by refreshing the mapping: evidence regenerated with
   the target's own deterministic builder
   (recordAgentSupervisorSemanticBaseline +
   serializeAgentSupervisorSemanticBaselineEvidence; new baseline digest
   sha256:7499edcb…, repository revision sha256:cad9bf59…; 7 known
   pre-change failures remain, the repaired one gone), and the test's
   expected code list updated to match. The same stale expectation in
   test/browser/verified-gui-optimizer-agent-supervisor-boundary.test.ts
   (line 402) was reconciled the same way — it now asserts the
   still-flagged 'outerhtml-root-replace-focus-risk' is present and the
   repaired code is absent; its archived-defect receipt assertions
   (ORIGINAL_DEFECT_CODES at lines 258/695) are untouched. The e2e specs
   (test/e2e/verified-gui-optimizer-agent-supervisor-{baseline,regression}
   .spec.ts) reference the code as an ORIGINAL_DEFECT_CODES fixture for
   the VGO improvement loop's before-state and were deliberately NOT
   edited; they belong to that lane's lifecycle.
After fixes: the 6-file focused batch (codec, web-renderer,
dashboard-policy, baseline, boundary, console-gateway) is 66/66 PASSED.
- Verified-GUI-optimizer board re-run after npm ci: the two .bin errors
  cleared; only the sealed-toolchain pins remain (wants Node v22.19.0 /
  npm 10.8.2 exactly; host 24.20.0 / 10.9.4). The npx provisioning route
  was interrupted twice by VM restarts and a nodejs.org fetch stalled; the
  pin gap is documented, not worked around by changing the board.
- DCR board and FACP results stand as recorded above (DCR: bootstrap-only
  failures on the shared checkout, per doc 48 itself; FACP valid:true).

### WS3 — visual check, completed (see visual_check/REPORT.md)
Served swissknife/web statically (127.0.0.1:8901) and captured with
Playwright/Chromium: 01-virtual-desktop, 02-agent-supervisor-console,
04/05-mcp-control, 06-mcp-plus-plus-app, 07/09 steering form,
08/10 steering error state (+ capture_log*.json, probe2.json). All views
exist and render; with no gateway running they show their designed
degraded/fallback/unavailable states (console: degraded + fallback with
goals/queue/receipts; MCP++ Explorer: UNAVAILABLE, 0/3 services, cards for
IPFS Kit / Datasets / Accelerate with VDA-G053 peer/Event-DAG diagnostics;
MCP Control: zero-daemon empty state per the browser-truth policy).
Steering field-to-error association verified LIVE: on an invalid submit,
role=alert element agent-supervisor-steering-error
("scope_not_allowed — Prompt text must be present and no longer than 8000
characters"), textarea with aria-invalid + aria-describedby +
aria-errormessage pointing at it, submit with aria-describedby.
One cosmetic defect documented in the report (not fixed; presentation
layer, outside the scoped interfacing surface): MCP Control header —
status-legend fragments overlap/clip the window title and non-selected
category rows render at very low contrast; structure localized to
.mcp-header inside .mcp-control-app.enhanced; no stylesheet 404s.

### Integration re-run
python -m pytest tests/integration -q (superproject venv), after all
fixes above: **526 passed, 31 skipped, 0 failed** in 162.76 s — identical
to the morning's baseline. (A first attempt was killed by a VM restart at
51%; the completed re-run was on a quieter machine, hence the shorter
wall time vs the morning's ~25 min.)

### Final tree state after the verification pass (for the record)
- Superproject: the morning's modified files, plus this pass's
  implementation_plan/evidence/verified_gui_optimizer/
  agent-supervisor-semantic-baseline.json (regenerated, above) and
  agent-supervisor-regression-receipt.json (refreshed as a side effect of
  running the VGO-081 boundary test, which rebuilds its regression
  receipt). Untracked: SWISSKNIFE_FIX_NOTES.md, visual_check/.
  The Mcp-Plus-Plus pointer shows modified only because of the untracked
  Lean build byproducts (.lake/, lake-manifest.json) in that tree.
- swissknife: the morning's 6 files plus this pass's 3 test files
  (mcp-dashboard-browser-policy.test.ts,
  agent-supervisor-baseline.test.ts,
  verified-gui-optimizer-agent-supervisor-boundary.test.ts).
- Nothing committed, nothing pushed, in any tree.
