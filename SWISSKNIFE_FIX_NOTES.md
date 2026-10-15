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

## Hold acknowledgment (2026-10-13, ~15:05 PDT)
Per the coordinator's notice (Benjamin's direct instruction): the morning's
fix set is being committed by the coordinator with explicit pathspecs
covering only the morning's files plus submodule-pointer bumps. I am
HOLDING all source edits inside the three repo trees (superproject tracked
files, swissknife/, external/ipfs_accelerate/) until the coordinator
confirms the commit is complete; read-only work, /tmp probes, Lean work,
and visual_check/ captures may continue. My verification pass was already
complete and reported before this notice arrived. My verification-pass
change set — swissknife's 3 test files (mcp-dashboard-browser-policy,
agent-supervisor-baseline, verified-gui-optimizer-agent-supervisor-
boundary), the regenerated agent-supervisor-semantic-baseline.json
evidence, and the boundary test's regression-receipt refresh — is NOT part
of the coordinator's commit pathspecs; it stays uncommitted as a separate,
clearly-listed change set (see the completion addendum above) to be
committed separately later, not by me.

## Hold released — committed baseline verified (2026-10-13, ~15:06 PDT)
The coordinator's commit landed and was verified against live state (not
taken on trust): superproject main 22d7c782b, swissknife f2972b38,
external/ipfs_accelerate 125a0b87f — matching the release notice exactly.
Only the morning fix set was committed. My verification-pass change set is
intact and uncommitted on top of the new baseline: swissknife's 3 test
files (porcelain shows exactly those three), the two
verified_gui_optimizer evidence JSONs, SWISSKNIFE_FIX_NOTES.md's
post-commit appends, and untracked visual_check/. Standing state noted,
not touched by me: pre-existing .handsfree_transport_sessions.json
modification; Mcp-Plus-Plus pointer noise from the untracked Lean build
byproducts; accelerate's nested-submodule pointer markers; the
external/ipfs_datasets working-tree state from the morning's restore.
Re-verification against the committed baseline: focused Vitest batch
66/66 passed; integration suite re-run result appended below when it
lands. I remain the non-committing party for my change set — it will be
committed separately later.

Integration suite re-run on the committed baseline (22d7c782b + my
uncommitted change set): **526 passed, 31 skipped, 0 failed** in
370.90 s — identical to the morning's baseline and to the post-fix
pre-commit run. Verification pass is complete on the committed baseline;
the change set listed above remains uncommitted for separate later
committing.

## Functional verification + broken-contract map pass (2026-10-13, later session)

Scope: Benjamin requires (A) functional verification — visual checks WITH the
backend live, driven against program state, exercising each app's primary
features end to end; (B) a broken-contract map — ORB/IDL + MCP++ interface
contracts compiled into proof obligations via ipfs_datasets_py.logic,
classified proved / refuted (counterexample) / blocked (exact reason), and
cross-referenced against (A) both ways. Fixes only for proven breaks inside
the SwissKnife ↔ MCP++ interfacing scope, as descriptor/registration/
binding/schema-alignment changes (DCR operator families). Nothing committed.

Launch routes discovered (repos' own):
- Desktop + gateway: swissknife vite dev server (`vite dev --config
  vite.web.config.ts`, port 3001) serves web/ AND installs the same-origin
  mediator middleware: GET /mcp/tools/bindings (control catalog from
  ALL_APP_LIVE_TOOL_BINDINGS + live tools/list discovery), GET
  /mcp/apps/backend-status, POST /mcp/tools/call (MCPPPServerConnector,
  Profile A/C + UCAN verification; receipts persisted via kit
  /mcp/artifacts/put), and /mcp/services/<owner>/mcp/* proxying.
- Owner MCP endpoints (vite defaults): ipfs_kit_py 127.0.0.1:8014/mcp,
  ipfs_datasets_py 127.0.0.1:3002/mcp, ipfs_accelerate_py 127.0.0.1:3003/mcp
  (env overrides SWISSKNIFE_IPFS_{KIT,DATASETS,ACCELERATE}_MCP_URL, or
  lease files in test-results/virtual-desktop-ipfs-mcp-orb/).
- Owner servers: the repos' own compat adapters
  swissknife/scripts/start-ipfs-{kit,datasets,accelerate}-mcp-compat.cjs
  (Node HTTP servers implementing MCP JSON-RPC + Profiles A/B/C/E/H,
  /mcp/health, /mcp/helia/status, /mcp/dag/*, /mcp/artifacts/put; tool
  catalogs loaded from the Python repos). Author-machine paths are
  env-overridable: IPFS_KIT_PYTHON, IPFS_DATASETS_PY_ROOT — point them at
  this checkout's .venv and external/ipfs_datasets.

## Correction — VGO board sealed-toolchain check CLOSED (2026-10-13, later)
The addendum above recorded the verified-GUI-optimizer board as failing on
the sealed-toolchain pins because the npx provisioning was believed
interrupted. A late background-completion delivery showed the provisioning
had in fact succeeded (~/.npm/_npx/759e7e0cbbdd6854 contains node v22.19.0
+ npm 10.8.2). Re-run with that toolchain prepended to PATH:
scripts/validate_verified_gui_optimizer_board.py --check-all →
{"errors": [], "valid": true} (12 goals / 42 tasks / 21 waves). All three
board validators are now resolved: FACP valid:true, VGO board valid:true,
DCR board valid:false on bootstrap/source-binding only (the documented
shared-checkout preflight state per doc 48 §15, not an interfacing
defect).

#### Checkpoint: stack live + deletion-blocked checks re-run (2026-10-13, post-restore)

Coordinator confirmed the external/ipfs_datasets restore: all 10,447 deleted paths
restored from HEAD; the tree's only remaining status entry is the preserved modified
legal_scrapers czechia normalize.py. Re-runs of the previously DELETION-BLOCKED checks
(this worker did not touch that tree; datasets suite run read-only with
PYTHONDONTWRITEBYTECODE and an out-of-tree pytest cache dir):

- Superproject tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py: 33 passed
  (previously skipped). 
- Datasets in-tree suite external/ipfs_datasets/tests/unit/logic/ui_ux_ir/ (284 passed,
  2 failed): (1) projection/test_solver.py::test_solver_is_deterministic — two solver
  runs yield different digests (sha256:cc71... vs sha256:9d59...): a genuine determinism
  counterexample in the ipfs_datasets projection solver, outside the SwissKnife-MCP++
  interfacing fix scope; carried into BROKEN_CONTRACT_MAP.md. (2)
  test_domain_slice.py::test_ui_ux_adapter_note_declares_required_contract_fields —
  FileNotFoundError: the test searches ancestors of its own file for
  data/agent_supervisor/logic_platform_canonicalization/notes/intent_uiux_adapters.md;
  the note exists at external/ipfs_accelerate/data/... (sibling, not an ancestor, in the
  submodule layout) and does declare the required fields (verified by direct read).
  Layout-blocked, not a contract break.
- SwissKnife cross-language golden vectors (test/mcp-plus-plus/
  ui-ux-ir-cross-language.test.ts, golden_vectors.json fixtures): 4 passed — previously
  unrunnable while fixtures were deleted.

Live stack (repos' own launch routes; bring-up script preserved at
visual_check/fv_state/bring-up.sh): ipfs_accelerate_py.mcp_server --fastapi on
127.0.0.1:9000; swissknife compat adapters kit :8014 / datasets :3002 / accelerate :3003
(scripts/start-ipfs-*-mcp-compat.cjs); vite dev (vite.web.config.ts) on :3001 serving
the desktop + /mcp mediator. Program state captured under visual_check/fv_state/:
tools/list kit 124, datasets 319, accelerate 18; gateway /mcp/tools/bindings = 79
controls, all status=available; /mcp/apps/backend-status matrix over 135 statuses:
79 live, 3 denied, 32 unavailable, 15 local-only, 6 external-provider.

Environment note: the VM rebooted mid-pass (uptime reset, /tmp wiped, background
processes killed). Recovery was via the persisted bring-up script; all run state now
lives under visual_check/fv_state/ instead of /tmp.

#### Fix F1 (verification change set): SVD-132 Playwright driver import alignment

The SVD-132 real-browser audit (npm run test:e2e:app-audit-runner) failed to load:
"SyntaxError: The requested module './virtual-desktop-app-audit-runner.js' does not
provide an export named 'resolveVirtualDesktopAppId'". The driver imported the resolver
from the audit runner; the runner imports it from virtual-desktop-app-manifest.ts
(where it is defined, line 1132) but never re-exports it. Fix: the driver now imports
resolveVirtualDesktopAppId from './virtual-desktop-app-manifest.js' (its canonical
module, the same source the runner and the manifest test use); the driver's own
re-export for callers is unchanged. One import binding aligned; no behavior or test
changes. File: swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver.ts.

#### Checkpoint: live proofs + SVD-132 audit timeout + retry (2026-10-13)

- Objective B live-state obligations discharged through ipfs_datasets_py.logic
  Z3ProverBridge (TDFOL, propositional finite-fact encoding over the captured live
  state; driver visual_check/fv_state/prove_contracts.py): 9/9 PROVED —
  P-discovery-parity {kit, datasets, accelerate} (every gateway control's
  selected_tool_id is in its owner's live tools/list: kit 124 tools, datasets 319,
  accelerate 18; 79/79 controls), P-foreign-exclusion x3, C-tool-backed-completeness
  (all 38 tool_backed apps have >=1 available control), C-mutation-requires-
  confirmation, S-status-coherence (135 statuses: states all in the declared set,
  every non-live status reasoned, denied statuses policied).
- SVD-132 real-browser audit, first run after Fix F1: exceeded its own 900000 ms
  Playwright test timeout at ~18/48 apps (~50 s/app: dual-viewport screenshots +
  close/reopen cycles against a cold vite dev server on this loaded VM). No evidence
  JSON written (the spec writes only on completion); 18 app screenshot directories
  remain under test-results/.../app-screenshots/svd-132-playwright/. Disposition:
  BLOCKED-BY-RUNTIME-BUDGET in this environment, not a product defect. Retrying once
  with a warm node_modules/.vite cache and no competing load; the lean fv_state
  drive (desktop.launchApp over all 48 ids + feature exercise) is the fallback
  primary evidence.
- MCP glasses prereq chain (npm run evidence:mcp-glasses) failed at
  capture-ipfs-mcp-all-tools-ledger.cjs under the chain (exit 1, no detail logged),
  but the same script run directly exits 0 (ledger: 100 exact tool records, 55
  configured-live, 45 static-descriptor; real_local_accelerate_tool_count = 0 — the
  accelerate upstream's real tool catalog is not reachable in the shape the capture
  expects; cf. the upstream /mcp/tools 422 without a `request` query parameter).
  Chain re-run planned after the audit retry.

#### SVD-132 retry disposition (2026-10-13)

Retry of the SVD-132 real-browser audit (warm vite cache, no competing load) paced
identically (~35-50 s/app) and was stopped at ~11 min in the same first-~18-app
frontier; two runs establish the route cannot meet its 900 s budget on this VM.
Final disposition: BLOCKED-BY-RUNTIME-BUDGET (test-infrastructure pacing), with the
18 apps' screenshot sets from run 1 as partial corroboration. Primary Objective A
evidence is the lean drive (fv_state/drive.mjs) over the same window.desktop
launchApp/focusWindow/closeWindow API for all 48 ids plus feature-level exercise.

#### Fix F2 (verification change set): SVD-132 driver close path alignment

Runtime probe of the served desktop (web/index.html loads web/js/main-simple.js)
shows window.desktop (SwissKnifeDesktop) exposes launchApp and focusWindow but NO
closeWindow method (own + prototype enumerated live). The full web/js/main.js
implementation defines closeWindow (line 2261) but is not the served entry. The
SVD-132 Playwright driver's closeApp called desktop.closeWindow(entry.element) —
a TypeError for every app, so its close/reopen evidence could never succeed
against the served shell. The shell's own close path is the titlebar control
(.window-control.close), whose handler deletes the window from the tracking map
and removes the element — the same click the shell's in-window Close buttons
dispatch. Fix: the driver's closeApp now clicks that control and verifies the
window left the tracking map. File:
swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver.ts.
User-facing impact of the underlying divergence: none found — the served shell's
own UI closes windows correctly through the control; the break was confined to
the audit driver's assumed programmatic interface.

#### Environment: second VM reboot (2026-10-13)

The VM rebooted a second time mid-pass (uptime reset; all loopback servers killed;
workspace intact). Earlier drive stalls (drive1 at strudel, drive2 at strudel-ai-daw,
drive3 at image-viewer/notes) are re-attributed: they coincide with reboot onsets,
not app launch defects — no app-hang claim is carried into the deliverables without
a clean re-run. The drive now writes per-app results incrementally (JSONL) so a
reboot can void at most one app record. Stack recovery is the idempotent
visual_check/fv_state/bring-up.sh.

#### Final results: functional verification + broken-contract map (2026-10-13)

Deliverables: visual_check/FEATURE_MATRIX.md and BROKEN_CONTRACT_MAP.md (repo root).

Objective A (live stack: vite :3001, kit :8014/124 tools, datasets :3002/319,
accelerate :3003/18 + upstream :9000, datasets dashboard :8899):
- 45/45 canonical apps open/focus/close cleanly (drive fv_state/drive.mjs,
  drive-apps.jsonl). Aliases launch only via the manifest resolver (map X1).
- MCP++ Explorer discovers 461 tools across 3 negotiated services; header DEGRADED
  traces to mcp++/risk/profile -32601 on all adapters (map R1). Explicit tool call
  passes with the full datasets stack (adapter + dashboard :8899).
- MCP Control mediated invocation EXECUTED end to end (policy allow, CID receipt,
  Event-DAG id). Agent Supervisor steering: unconfirmed submit policy-denied;
  confirmed dry-run produced normalized plan + correlation + receipt.
- SVD-132 real-browser audit blocked by its own 900 s budget at ~18/48 apps (B1).

Objective B: 22 obligation groups — 14 proved (incl. 9/9 live-state Z3 obligations
via ipfs_datasets_py.logic Z3ProverBridge over captured program state; MCP-IDL
identity 33 passed post-restore; golden vectors 4 passed; ORB/IDL coverage
regenerated 45/45 descriptors), 3 refuted (R1 risk/profile — not fixed, adapter
implementation is out of alignment scope; R2/R3 SVD-132 driver interface — FIXED
F1/F2; R4 datasets solver determinism — datasets-owned), 1 boundary (X1 aliases),
4 blocked with exact reasons (B1/B2 runtime budget, B3 checkout layout, B4 sealed
evidence for DCR live conformance; @ucans/ucans import verified resolved).

Post-restore re-runs: datasets ui_ux_ir suite 284 passed / 2 failed (R4, B3);
superproject forwarding file 33 passed; integration suite 528 passed / 29 skipped /
0 failed (baseline 526/31/0 — delta is the restore un-blocking 2 tests).

Fix change set (uncommitted, this pass): ONLY
swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver.ts (F1+F2).
Everything else is evidence/tooling: visual_check/fv-*.png, visual_check/FEATURE_MATRIX.md,
visual_check/fv_state/*, BROKEN_CONTRACT_MAP.md, regenerated evidence under
swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ (orb-idl-complete-coverage.json,
glasses-simulator-handoff.json, refreshed ledgers/catalogs), and these notes.
Environment provisioning (not repo changes): flask installed into the venv for the
datasets dashboard. Nothing committed.

#### Addendum: graded vitest confirmation (2026-10-13)

vitest run of test/mcp-plus-plus/virtual-desktop-app-manifest.test.ts +
desktop-orb-idl-contract.test.ts: 21 passed / 0 failed (incl. the SVD-132 graded
simulated-driver determinism check — byte-identical evidence across two runs — and
SWR-108 ORB/IDL coverage). The run's single "unhandled error" is a vitest-worker
onTaskUpdate RPC timeout (reporting channel on this loaded VM), not a test failure.
This confirms F1/F2 leave the graded SVD-132 path intact.

#### Erratum (2026-10-13, post-report verification): SVD-132 evidence file

A late-delivered monitoring result prompted re-checking svd-132-playwright.json: the
file EXISTS (run of 2026-10-13T23:35Z, post-F1/pre-F2). The runner completed its
sweep and wrote it as the test crossed its 900 s budget: 48 apps recorded,
0 passed / 48 failed, 26 of 96 screenshots captured. Every app's close_reopen.error
is the R2 counterexample verbatim ("page.evaluate: TypeError: desktop.closeWindow
is not a function"); the back ~34 records carry timeout-teardown contamination.
Earlier statements in these notes and the first B1/F-09 drafts ("no evidence JSON
written", "timeout at ~18/48 apps" — the 18 was the complete-screenshot-set count)
are corrected in BROKEN_CONTRACT_MAP.md (B1, R2) and visual_check/FEATURE_MATRIX.md
(F-09). The B1 disposition is unchanged: BLOCKED-BY-RUNTIME-BUDGET, with the file
itself as the strongest R2 evidence.

## Gap-closure pass (2026-10-13, later session — Benjamin: "solve the gaps so all backends work, fix all broken contracts")

Scope EXPANDED by Benjamin's directive: source fixes are authorized where a
contract is refuted. Worklist = BROKEN_CONTRACT_MAP.md R1, X1, R4, F-06 gateway,
B6, B2, B4, B1; disposition-only B5/B7/B3. All fixes stay UNCOMMITTED, listed
file-by-file. Baseline: superproject 8ce1bb13, swissknife cd37eeb4,
external/ipfs_accelerate 125a0b87f.

### R1 investigation (mcp++/risk/profile)
- Client: web/js/core/mcp-plus-plus-desktop-client.js calls RPC
  mcp++/risk/profile on every service in inspectService (profileG probe);
  also getRiskSchedulingProfile + gateway mapping 'supervisor.profile-g.read'.
- Canonical shapes: datasets ProfileGService.profile (provider ipfs_datasets_py,
  interface_descriptor + interface_cid, methods[23]); accelerate transport
  profile_metadata() fallback {version, artifact_schema_major, provider,
  transports, methods}; kit RuntimeProfileG.metadata() via its dispatcher
  (risk/profile is in kit's _LOCAL_RUNTIME_METHODS).
- Baseline live: all three adapters -32601 (re-verified this session).
- UPSTREAM BUG FOUND: accelerate upstream GET /mcp/risk/profile returns
  422 (missing query 'request') then 500: pydantic PydanticUserError
  "TypeAdapter[Annotated[ForwardRef('Request'), Query(...)]] is not fully
  defined". Cause: fastapi_service.py has `from __future__ import annotations`
  and imports Request only inside create_fastapi_app(); FastAPI resolves the
  handler's `request: Request` annotation from module globals, where Request
  is absent -> treated as a required query param. The whole Profile G REST
  facade (and Profile D policy evaluate, same pattern) is dead in the running
  build. Enabling fix F3: module-level Request import in fastapi_service.py.
- Plan: new shared module swissknife/scripts/mcpplusplus-profile-g-adapter.cjs
  (mirrors profile-h adapter idiom). Per owner: accelerate -> proxy upstream
  GET /mcp/risk/profile (normative REST binding); kit -> spawn Python kit
  get_dispatcher().dispatch('mcp++/risk/profile', {}); datasets -> spawn
  Python get_profile_g_service().dispatch('mcp++/risk/profile', {}).
  Backend failure -> G_PROVIDER_UNAVAILABLE (-32051, retryable) with data
  {code, message, retryable, details:{method}} — never a fabricated profile,
  never -32601. Result cached 60 s per adapter process. RPC branch +
  GET /mcp/risk/profile REST route added in all three adapters.

#### Gap-closure checkpoint: R1 FIXED + verified live; R4 FIXED (2026-10-13, later session)

**R1 — mcp++/risk/profile in all three compat adapters: FIXED.**
New file `swissknife/scripts/mcpplusplus-profile-g-adapter.cjs` (mirrors the
Profile H adapter idiom): per-owner backend resolution, success cached 60 s,
failures cached 5 s, wire Profile G error codes mapped through the canonical
ERROR_NUMBERS table, provider failure reported as -32051
G_PROVIDER_UNAVAILABLE (verified against a dead upstream — never fabricated).
- kit (:8014): dispatches the checkout's own
  `ipfs_kit_py.mcp_server.mcplusplus.profile_g_transport` dispatcher
  (RuntimeProfileG) in a Python subprocess (PYTHONPATH kit+datasets+accelerate).
- datasets (:3002): dispatches
  `ipfs_datasets_py.mcp_server.profile_g_service.ProfileGService`
  (provider ipfs_datasets_py, full limits + interface descriptor + CID).
- accelerate (:3003): proxies the upstream's native REST binding
  GET {upstream}/mcp/risk/profile.
All three adapters also serve `GET /mcp/risk/profile`. RPC + REST verified by
direct probe on all three ports.

Enabling source fix **F3** — `external/ipfs_accelerate/ipfs_accelerate_py/
mcp_server/fastapi_service.py`: the Profile G REST facade was dead in the
running build. `from __future__ import annotations` + `Request` imported only
inside `create_fastapi_app()` left the handlers' `request: Request`
annotation an unresolved ForwardRef, so FastAPI treated it as a required
query parameter (GET /mcp/risk/profile -> 422; 500 PydanticUserError with
`?request=` supplied). Fix: module-level `from fastapi import Request`
(guarded, `Any` fallback) — the same pattern had also broken Profile D
`POST /mcp/policy/evaluate`'s annotation. After restart the upstream returns
its genuine profile (provider ipfs_accelerate_py metadata profile).

Adapter liveness fix (same item): the Python bridge originally used
`spawnSync`, which froze the adapter event loop for the whole cold dispatch
(datasets ~30 s under load), starving that adapter's health/initialize
probes past the desktop client's 8 s timeout during parallel inspection —
the mechanism behind the Explorer's flaky "N/3 responded" counts (observed
2/3 and 1/3 across runs; the prior pass's own drive capture also recorded a
0/3 moment). Bridge is now async `spawn`; kit + datasets adapters warm the
profile dispatch at startup. Datasets interfaces/frontier probes also hang
without the datasets dashboard on :8899 (prior pass ran it as a separate
step); with the dashboard up frontier answers in 0.23 s. Residual cold
costs (not availability-gating): first interfaces/list per adapter start
(kit ~50 s, datasets ~22 s descriptor build; cached afterwards).

**Live verification (cold full-stack restart via bring-up.sh + dashboard):**
MCP++ Explorer header: state `ready`, "3/3 MCP++ services responded.",
124 + 319 + 18 = 461 tools, all capability tags negotiated. Screenshot
`visual_check/fv-11-explorer-healthy.png`; probe results
`visual_check/fv_state/explorer-probe-results.json`.

**R4 — ui_ux_ir projection solver determinism: FIXED.**
Root cause: `SolverBoundsReceipt.elapsed_ms` (wall-clock solve duration)
was serialized by `to_dict()`, so `UIProjectionArtifact.digest()` — billed
as a deterministic artifact with a stable content digest — differed between
identical solves (field-level diff of two in-process runs: only
`/bounds/elapsed_ms` varied, 16 vs 0). Fix in
`external/ipfs_datasets/ipfs_datasets_py/logic/ui_ux_ir/projection/solver.py`:
`elapsed_ms` excluded from `SolverBoundsReceipt.to_dict()` with an
explanatory comment; the attribute remains on the receipt object (the
`bounds.elapsed_ms >= 0` test still passes) and the live max_solve_ms bound
check in `_SolveState.tick` is untouched. No other consumer reads the
serialized field (repo-wide grep). Suite: `tests/unit/logic/ui_ux_ir` =
**285 passed, 1 failed** — the one failure is B3 exactly as typed
(checkout-layout note discovery; the note itself verified compliant by
direct read in the prior pass). Baseline was 284 passed / 2 failed.

#### Gap-closure checkpoint: X1 FIXED; console gateway stood up (item 4); B6 closed (2026-10-13, later session)

**X1 — served-shell alias resolution: FIXED.**
`swissknife/web/js/main-simple.js`: added a mirror of the manifest's
VIRTUAL_DESKTOP_ALIAS_TO_ID (code-editor->vibecode, strudel-grandma->strudel,
p2p-chat-offline->p2p-chat) + resolveVirtualDesktopAppId with the TS
resolver's semantics (canonical passthrough, alias -> canonical, unknown ->
null); launchApp resolves before lookup so windows register under the
canonical id and singleton/smoke/backend mounts all see the canonical id.
Live probe (visual_check/fv_state/alias_probe.mjs): all 3 aliases open +
close their canonical windows; canonical launch unchanged; unknown id stays
a clean no-op. No user-facing surface used raw aliases before (icons/start
entries are canonical) — this closes the raw-form refutation in the map.

**Item 4 — supervisor console gateway: STOOD UP + VERIFIED LIVE.**
Finding: there is no separate console-gateway server artifact in the repo.
The console's production gateway is the MCP++ desktop client's
createSupervisorGateway() (browser-side; health via inspectAll, state reads
mapped onto Profile G). The served shell never installed it for the console:
the Explorer publishes it as window.swissknifeMCPPlusPlusSupervisorGateway
(a name the console never reads) and window.__AGENT_SUPERVISOR_GATEWAY_ENDPOINT__
is set nowhere. Fix: main-simple.js createAgentSupervisorApp now installs
the client gateway as window.agentSupervisorGateway when no gateway/endpoint
is configured (explicit configuration still wins; failure leaves the
designed fallback intact).
Supporting adapter work (same pass): the Profile G bridge was generalized
from risk/profile only to the full canonical 23-method set —
accelerate proxies the upstream's normative REST bindings (writes reach
the upstream's own validation, e.g. goals/create {} -> G_INVALID_ARTIFACT);
kit/datasets dispatch through a PERSISTENT Python worker process
(JSON-lines over stdio, one per adapter) instead of a spawn per call:
backend import paid once at the adapter-start warm-up, warm reads ~0.0 s
(were 6-30 s), and Profile G state lives for the adapter process lifetime,
mirroring the upstream's in-process store semantics.
Live console probe (visual_check/fv_state/console_probe.mjs; screenshot
fv-12-supervisor-console-live.png): status ready, transportMode degraded
(NOT fallback), health status available with all 3 backends available
(124/319/18 tools, zero diagnostic errors, live server_time), snapshot
queue/goals/receipts = 0/0/0 LIVE (the fallback sample was 4/2/4 with
fixture titles). The only capability errors are the 5 the production
gateway deliberately does not map (taskboard.links, logs, run-history,
policy.assist, semantic-goal.assist -> typed capability_unavailable) —
that is the gateway's own contract, recorded here rather than papered over.
Environment note: a VM reboot mid-pass killed vite + the datasets
dashboard (both relaunched); a co-tenant OCR burst (load ~11) makes the
browser's 8 s probe timeouts flap between windows — both browser proofs
were re-captured in a clean window (Explorer 3/3 ready; console as above).

**B6 JevOps: CLOSED.** Cloned endomorphosis/JevOps (public, shallow) to
~/lift_coding/JevOps (the sibling path _jevops_path.py requires).
tests/test_lra_track1_mistral.py collects 21 tests (was the `make test`
collection blocker); full-suite collection now completes: 3,273 tests
collected, 0 errors.

#### Gap-closure checkpoint: B4 live libp2p session PROVEN (2026-10-13, later session)

**B4 — live host-to-host MCP++ session: PROVEN (same-machine two-host).**
Installed the repos' own pinned py-libp2p into the lift_coding venv
(libp2p 0.7.0 @ git commit 20d9527f, the mcp-p2p extra from
ipfs_accelerate_py's pyproject / libp2p_runtime.PY_LIBP2P_PINNED_SPEC).
Session script `visual_check/fv_state/p2p_session.py`, evidence
`visual_check/fv_state/p2p-session-evidence.json`: two MCPp2pNode hosts
(repos' Profile E transport, real py-libp2p TCP/Noise/yamux) on loopback
ephemeral ports — server peer 16Uiu2HAm9rtQVsMcqe2zjt8iBBqwDPsPysosMiEKuoFZW9j4nkC4
(/ip4/127.0.0.1/tcp/44203), client 16Uiu2HAmF4k7VCUXhqpsqhM9dYP4CyJJ3ZjBhD2sazwXhhVL3J5U,
both operational. Client connected via the node's own bootstrap-connect
path; over /mcp+p2p/1.0.0 streams it (1) fetched the server's Profile A
interface descriptor (CID bafybeiaa5la7h3cy44kxqm2mzczly3bmyuvvfhynlafnq2zxeqmpcn7pue),
(2) executed a UCAN-gated tool call: delegation CID
bafybeig5qtygertjyn... evaluated server-side by cid_ucan's
DelegationEvaluator.can_invoke -> authorized; execution receipt CID
bafybeiarmkf4mbgc5gwngkrucz53ez5lwh5q7fnf7sz4qqmvdhrgczks2i; the server's
handler saw the client's real peer id as _sender_peer_id, matching the
client host's identity, and (3) refused both negative controls
(wrong-resource delegation: "No delegation in chain grants 'invoke' on
'tools/echo'"; no delegation: "delegation required"). This is a
same-machine two-host session — real transport, no mocks — stated plainly
per the worklist. Sealed DCR service evidence: NOT generatable from this
tree — implementation_plan/docs/48 records the DCR bootstrap as sealed on
a dedicated clean integration branch and "sealed current evidence" as
still required; that remainder of B4 stays typed (the @ucans/ucans half
was already resolved in the functional pass).

#### Gap-closure checkpoint: closing integration suite GREEN (2026-10-13)

`python -m pytest tests/integration -q` after all gap-closure fixes:
**528 passed, 29 skipped, 0 failed** in 223.37 s — identical to the
functional-pass baseline (log: visual_check/fv_state/integration-gap-pass.log).
No regressions from F3/G1/G2/G3/G4. BROKEN_CONTRACT_MAP.md dispositions and
FEATURE_MATRIX.md rows updated in place (R1/X1/R4 fixed, B4 narrowed, B6
closed, console row resolved, new F-11/F-12 rows). Remaining at this
checkpoint: B1 (SVD-132 completion attempt) and B2 (SWR-096/102 producer
runs) — both gated on a quiet window (co-tenant OCR load ~11-14 makes the
in-spec 180 s/900 s budgets unreachable; the producers die mid-run under
that load, measured).
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
- B1: canonical single-run artifact not produced on this 2-core VM (needs ≤18.75 s/app vs ~29 s/app measured at load ~12, minutes/app at load 18-39). Discharged via the runner-supported batched route: 3 completed batch runs, 37/48 ids audited, 33 passed, 74/96 screenshots (assembly: visual_check/fv_state/svd132-batched-assembly.json). Failures: terminal/github/media-player (wallpaper egress only), strudel-ai-daw (B7). Remaining 11 ids attempted twice more under load 18-39 without completing; all 48 are covered by the drive sweep + alias probe.
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

## Per-app MCP++ interaction-design audit (sharpened requirement, 2026-10-14)

Benjamin's sharpened emphasis: "make sure that the SwissKnife GUI apps are
actually properly designed to interact with the backend services over
MCP++." Audit of all **38 tool_backed apps** against the LIVE stack (vite
mediator :3001, adapters :8014/:3002/:3003, upstream :9000, dashboard
:8899, Profile E bridges :9112/:9113/:9114). Harnesses + raw results under
`visual_check/fv_state/audit2/` (bindings.json, backend-status.json,
per_app_invocations.mjs → per-app-invocations.json,
ui_truthfulness_probe.mjs → ui-truthfulness.json, screenshot
`visual_check/fv-13-ui-truthfulness.png`).

### Step 1 — per-app mediated invocation (extends P1/P2 to execution)
Every app's representative control was invoked through `POST
/mcp/tools/call`, with calls constructed byte-for-byte as the apps' own
live-tool-gateway panel builds them (`web/js/live-tool-gateway.js`
invokeControl: same protocol, route, policy shapes, safe_payloads).
**38/38 apps executed** over http, each returning a receipt, an
Event-DAG ref, a persisted-receipt status (`persisted` for all 38), and
an `application_transport_observation` with a descriptor CID and
`ucan_did_verified: true`. No app lacked a safe control to fire:
non-mutating representatives executed live; mutating representatives
executed as the panel's governed dry run (step 4).

### Step 2 — transports (found R5, fixed; see below)
Live catalog: 79 controls — 57 declare http only, **22 declare
(http, libp2p) across 10 apps**, none libp2p-only; the catalog's
per-control `transport` default is http for all, and the panel selects
libp2p only via the `__SWISSKNIFE_GATEWAY_TRANSPORT_OVERRIDE__` replay
hook (recorded as a design fact: libp2p is a declared, mediator-exercised
transport, not the panel's default). The other 28 apps are http-only —
stated per app in the table (libp2p column "—").
After the R5 fix, the mediator-side libp2p route was exercised for every
declaring app (the same call the override produces): **10/10 executed**,
each with observation `{transport: 'libp2p', descriptor_cid,
ucan_did_verified: true, remote_did (the owner bridge's did:key),
identity_proof_cid}`.

### Step 3 — truthful UX state
- Data level: matrix ↔ catalog cross-check for all 38 apps — **zero
  mismatches** (available-control counts equal the matrix's live
  bindings per app).
- Browser level (Playwright probe, 8 apps spanning all owners +
  dispositions): every rendered panel control's disabled state and
  'ready' output matches the live catalog exactly (**0 mismatches**);
  the 2 sampled non-tool-backed apps (calculator, settings) mount **no**
  MCP++ panel at all — no fake affordances. The 7 non-tool-backed apps
  (settings, api-keys, oauth-login, calculator, clock, idl-explorer,
  glasses-preview) have no controls by design; dispositions
  browser_local ×5, policy_blocked ×1 (api-keys, credential isolation),
  external_provider ×1 — consistent with the functional pass's P4.

### Step 4 — confirmation design
Three layers, all verified live:
1. **Catalog**: mutating controls carry `confirmation_required` +
   `mutates_remote_state` (79-control catalog).
2. **Mediator (server-side)**: for every app whose representative is
   mutating (26 apps), a probe call with `dry_run: false` and consent
   NOT granted was **denied `confirmation_required` — 26/26**, before any
   adapter was touched.
3. **App UI flow**: the panel forces governed controls into
   `require_confirmation` + consent-granted + **dry-run-only** execution
   (it can never fire a live mutation); the repo's own graded e2e
   (`test/e2e/all-app-live-gateway-executions.spec.ts`) pins exactly
   this as the intended evidence class `confirmation_gated_dry_run`.
   Browser-verified: clicking vibecode's governed control
   (`...list_virtual_files`) produced `executed; …; receipt=bafkreihk…`
   as a dry run. The supervisor steering flow additionally has a literal
   user-confirm gate (P11, prior pass). Design note (not a break, per
   the repo's own spec): the panel shows no separate confirm dialog for
   governed controls precisely because it cannot execute them live; the
   dry-run character is carried in the policy record and the tool's
   echoed result.

### R5 — mediated libp2p path was dead; FIXED (2 files)
The desktop's Profile E route (mediator → announce file →
`scripts/invoke-mcp-libp2p.py` → owner bridge) could not execute at all
in this environment, for two stacked reasons, both in swissknife's
standalone Profile E scripts, which create py-libp2p hosts directly:
- `scripts/ipfs_mcp_libp2p_bridge.py` and `scripts/invoke-mcp-libp2p.py`
  never applied ipfs_accelerate_py's canonical
  `patch_libp2p_compatibility()` — the boundary the runtime module
  designates for ALL host creation. With pymultihash 3.x,
  `multihash.encode` is absent and py-libp2p 0.7 host creation crashes
  in `ID.from_pubkey` (all 3 bridges died at startup → no announces →
  mediator "No verified libp2p announce"). Proven in isolation: patch
  returns True, restores `encode`, `ID.from_pubkey` succeeds.
- The helper additionally imported `libp2p.tools.async_service`
  unconditionally (moved to `libp2p.tools.anyio_service.context` in
  py-libp2p ≥0.3 — the bridge already had the fallback; the helper
  didn't).
Fix (binding alignment, both files): each script now applies the
canonical patch at startup, resolving the sibling
`external/ipfs_accelerate` checkout (or `IPFS_ACCELERATE_PY_ROOT`) —
the helper does so inside its stdout→stderr import discipline; the
helper also mirrors the bridge's anyio import fallback. After the fix:
bridges start (`ensure-ipfs-mcp-libp2p-bridges.cjs`: 3/3 ready, valid
announces, Profile E 1.9.0), a manual Profile E session completes
(initialize → descriptor → UCAN identity → tools/call), and all 10
libp2p-declaring apps execute through the mediator (step 2).
Environment note (not edited): the mediator and the bridge launcher
default their Python to the author's workstation path
(`/home/barberb/...`) when `IPFS_ACCELERATE_PYTHON` is unset — the
designed override; this audit ran with it set to the lift_coding venv.

### Per-app results (representative control per app)
| app | controls avail/total | owner | http | libp2p | unconsented-mutation probe |
|---|---|---|---|---|---|
| terminal | 3/3 | datasets | executed | — | — |
| vibecode | 3/3 | kit | executed | — | denied |
| music-studio-unified | 2/2 | kit | executed | — | denied |
| ai-chat | 3/3 | datasets | executed | executed | — |
| file-manager | 2/2 | kit | executed | — | denied |
| task-manager | 2/2 | datasets | executed | — | denied |
| todo | 2/2 | kit | executed | — | denied |
| model-browser | 3/3 | datasets | executed | executed | — |
| huggingface | 3/3 | datasets | executed | — | — |
| openrouter | 2/2 | datasets | executed | — | denied |
| ipfs-explorer | 1/1 | kit | executed | executed | denied |
| device-manager | 2/2 | kit | executed | — | denied |
| mcp-control | 3/3 | kit | executed | executed | — |
| github | 2/2 | kit | executed | — | denied |
| cron | 2/2 | datasets | executed | — | denied |
| navi | 1/1 | datasets | executed | executed | — |
| p2p-network | 2/2 | kit | executed | — | — |
| p2p-chat-unified | 2/2 | kit | executed | — | denied |
| neural-network-designer | 2/2 | kit | executed | — | denied |
| training-manager | 3/3 | datasets | executed | — | — |
| calendar | 2/2 | kit | executed | — | denied |
| peertube | 2/2 | kit | executed | — | denied |
| friends-list | 2/2 | kit | executed | — | denied |
| image-viewer | 2/2 | kit | executed | — | denied |
| notes | 2/2 | kit | executed | — | denied |
| media-player | 2/2 | kit | executed | — | denied |
| system-monitor | 1/1 | accelerate | executed | — | denied |
| neural-photoshop | 2/2 | kit | executed | — | denied |
| cinema | 2/2 | kit | executed | — | denied |
| strudel | 2/2 | kit | executed | — | denied |
| strudel-ai-daw | 2/2 | kit | executed | — | denied |
| music-studio | 1/1 | kit | executed | — | denied |
| p2p-chat | 1/1 | kit | executed | — | denied |
| datasets-browser | 1/1 | datasets | executed | executed | — |
| accelerate-panel | 1/1 | accelerate | executed | executed | denied |
| orb-auto-ui | 3/3 | kit | executed | executed | — |
| mcp-plus-plus | 3/3 | kit | executed | executed | — |
| agent-supervisor | 3/3 | datasets | executed | executed | — |

## Interaction-coverage audit — continuation (audit3, 2026-10-14)

Benjamin's directive: make sure every user interaction in the GUI apps
actually connects to some feature of the ORB/IDL of the MCP++ interface to
one of the three backend services, especially the ipfs_accelerate_py agent
supervisor. The prior worker completed the inventory, static trace, and
supervisor deep-dive (`visual_check/fv_state/audit3/CHECKPOINT_2026-10-14.md`);
this continuation applied the six designed fixes, built the per-app trace
table, verified live on the real stack, and closed the docs. **All changes
are uncommitted** (a separate push integration is running; no git was run in
`external/ipfs_accelerate` or `external/ipfs_datasets`, and the preserved
czechia normalize.py was never touched).

### Fixes applied (each re-checked by the test/probe that exposed it)

1. **Console truthfulness leak (R6)** — `web/js/apps/agent-supervisor.js`:
   `readLiveSnapshot` no longer falls back per capability to
   `SAMPLE_SNAPSHOT`; unserved capabilities contribute empty lists (health an
   explicitly `unavailable` shell). SAMPLE renders only in full-fallback
   mode. Check: `audit3/check_fix1.mjs` PASSED; live probes show zero
   sample leakage.
2. **Steering dry-run regression (R7)** — same file: `withLocalSteeringPreview`
   restores the designed local no-mutation preview for dry runs only, when
   the gateway returns `unavailable/capability_unavailable`; confirmed
   submissions keep the typed error. Check: `audit3/check_fix2.mjs` PASSED
   (dry run → local preview receipt `rcpt-prompt-steering-*`; confirmed →
   typed `capability_unavailable` preserved).
3. **Gateway mappings (P16)** — `web/js/core/mcp-plus-plus-desktop-client.js`:
   `createSupervisorGateway` now maps `supervisor.logs.read` → accelerate
   `mcp++/dag/history` (real EventDag; events normalized to log entries),
   `supervisor.content.retrieve` → kit `GET /mcp/artifacts/<cid>`,
   `supervisor.receipts.persist` → kit `POST /mcp/artifacts/put`, and
   `supervisor.event-dag.checkpoint` → kit `POST /mcp/dag/append`. The two
   writes are governed: they deny with `confirmation_required` unless the
   payload carries the console's reviewed `confirmation_token`. For
   persist, the gateway computes the canonical CIDv1-raw+sha2-256 over the
   stable-stringified receipt bytes (mirroring
   `scripts/mcpplusplus-profile-a.cjs` `cidForBytes`/`stableStringify`),
   which the kit artifact store verifies byte-for-byte. Client gained a
   `post()` helper. Check: `audit3/check_fix3.mjs` PASSED against a stub
   whose fake adapter verifies CIDs with the production `cidForBytes`;
   live round-trip below.
4. **VDA-G054 (R8)** — `agent-supervisor.js`: the 8 workflow-proof buttons
   are bound in `bindEvents` to `handleWorkflowProofAction` (real pane
   navigation), and `renderVdaG054WorkflowProof` renders checkpoint/receipt
   refs only when the active snapshot carries them. Check:
   `audit3/check_fix4.mjs` PASSED; live tab navigation recorded.
5. **datasets-browser canned surface (R9)** — `web/js/main-simple.js`:
   `createDatasetsBrowserSurface` is async, imports the descriptor
   registry, and wires Search → `semantic_search`, Provenance →
   `record_provenance` (confirmed), Prepare → `index` (confirmed),
   Progress → `sync_status`; the schema/split selects are real
   `semantic_search` filter inputs; Apply Filters is a labelled local
   staging action; Recover Error is a labelled local pre-transport
   validation. All `bafydatasetg048*` CIDs and `receipt:datasets-browser:g048:*`
   strings are gone from render and log (grep count 0 across `web/js/`).
6. **accelerate-panel canned surface (R10)** — same file:
   `createAcceleratePanelSurface` is async and wires Run Inference →
   `run_inference_job` (confirmed) + `job_status`, Artifacts →
   `list_models`, Hardware → `hardware_profile`, Recover → `telemetry`.
   The fabricated "completed through the WebGPU path" claim and all
   `bafyaccelerateg049*` / `receipt:accelerate-panel:g049:*` strings are
   gone. Cancel has no descriptor operation: it reports that typed
   disposition (plus real `job_status` when a session job exists).

### Supervisor capability trace (the deep-dive's contract, after fixes)

| Capability | Owner | Disposition | Route / reason |
|---|---|---|---|
| supervisor.health.read | ipfs_accelerate_py | executes | desktop-client inspectAll across the three mediated services |
| supervisor.queue.read | ipfs_accelerate_py | executes | Profile G `mcp++/tasks/list` |
| supervisor.goals.read | ipfs_accelerate_py | executes | Profile G `mcp++/goals/list` |
| supervisor.subgoals.read | ipfs_accelerate_py | executes | Profile G `mcp++/goals/list` |
| supervisor.receipts.read | ipfs_kit_py | executes | Profile G tasks/list + per-task schedule status |
| supervisor.logs.read | ipfs_accelerate_py | executes (fix 3) | accelerate adapter `mcp++/dag/history` over its real EventDag, normalized |
| supervisor.receipts.persist | ipfs_kit_py | executes (fix 3) | kit `POST /mcp/artifacts/put`, confirmation-gated, canonical CID |
| supervisor.content.retrieve | ipfs_kit_py | executes (fix 3) | kit `GET /mcp/artifacts/<cid>` |
| supervisor.event-dag.checkpoint | ipfs_kit_py | executes (fix 3) | kit `POST /mcp/dag/append`, confirmation-gated |
| supervisor.prompt-steering.request (dry run) | ipfs_accelerate_py | local preview (fix 2) | designed local no-mutation preview; no backend steering route exists |
| supervisor.prompt-steering.request (confirmed) | ipfs_accelerate_py | typed-unavailable | `Supervisor.steer` exists in the accelerate facade; NO MCP adapter route serves it (B10) |
| supervisor.task-control.request | ipfs_accelerate_py | typed-unavailable | no gateway route for governed dispatch (B10) |
| supervisor.taskboard.links.read | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (B8) |
| supervisor.run-history.search | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (B8) |
| supervisor.policy.assist | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (B8) |
| supervisor.semantic-goal.assist | ipfs_datasets_py | typed-unavailable | zero implementations in ipfs_datasets_py (B8) |

Totals: 9 execute, 1 local preview, 6 typed-unavailable.

### Per-app interaction trace (exact counts)

Census computed from `audit3/inventory-raw.json`: **45 apps, 1,401 static
controls (1,095 buttons, 189 inputs, 86 selects, 31 textareas)**. (The
checkpoint's headline 1,443 does not reproduce from the file; the file is
authoritative.) Full per-app table: `audit3/TRACE_TABLE.md` /
`trace-table.json`, generated by `audit3/classify_trace.mjs`. Classes: the
38 tool-backed apps connect via the runtime-injected mediated panel (P15);
generated surfaces are classified control-by-control (datasets-browser 8 =
6 backend + 2 local; accelerate-panel 5 = 4 backend + 1 typed;
idl-explorer 6 = 3 + 3; orb-auto-ui 8 = 3 + 5; glasses-preview 7 = declared
browser-local; VDA-G054 section 8 = local navigation, fixed); the console's
static controls resolve to the capability table above; the remaining apps
are declared browser-local or external-direct (github, openrouter,
oauth-login, p2p-network). **Unmapped-and-fixed: 21 controls.
Unmapped-and-typed: 6 supervisor capabilities + accelerate Cancel.
Silently unmapped: 0.**

### Live verification (real stack, no mocks)

Stack via `visual_check/fv_state/bring-up.sh` + the datasets dashboard on
:8899. Probes: `audit3/live_probe.mjs` (cold stack),
`live_probe2.mjs` (warm re-drive), `live_probe3.mjs` (settle check);
screenshots `visual_check/fv-14…fv-17`.

- Console settled state: health **available**, all three backends
  available; error set = exactly the four B8 typed capabilities; queue /
  goals / receipts / logs all read live (0 items — this stack's Profile G
  and EventDag state is empty); **no SAMPLE leakage** in any probe.
- Fix-3 round-trip through the console's own gateway object: persist
  without confirmation → `denied/confirmation_required`; with the token →
  available, CID `bafkreidjbmeouqe42mu3uioynseoqgdtfjzrs3yiqv743jcxd56ftvpkw4`,
  backend `helia`, verified; retrieve → available, verified, 206 bytes;
  checkpoint → event CID `bafkreicbw5f2hfeflzmtksufkqfzfwxhl6i25qyiu7ui2ujhwzm7a6trwy`;
  logs.read → available. (Direct curl checks of the same routes through
  the vite mediator agree: artifacts put/get persisted+verified via helia,
  dag append returned a recorded event CID.)
- G054 navigation live: receipts → steering → health → active tabs all
  switched by the formerly dead buttons.
- datasets-browser live: no canned CID/receipt anywhere; all six buttons
  produced real gateway envelopes (status `degraded` — the browser
  app-capability gateway's designed descriptor-fallback for non-kit
  families, the same outcome the verified idl-explorer/orb-auto-ui show in
  this runtime); Apply Filters staged honestly; Recover Error produced the
  local validation message.
- accelerate-panel live: no canned refs, no WebGPU claim; Run Inference /
  Hardware / Artifacts / Recover produced real envelopes; Cancel produced
  the typed no-operation disposition.
- Two transient effects, both diagnosed, neither a defect of the fixes:
  (a) the first (cold) probe's Profile G reads timed out against cold
  Python worker bridges at load ~10 vs the client's 8 s timeout — the
  documented contention class from R1's root-cause note; the warm
  re-drive settled cleanly; (b) `receipts.read` flaked once with
  `server_unavailable` during a concurrent refresh burst while all three
  services answered `mcp++/tasks/list` instantly by direct RPC; the next
  refresh and a direct gateway invoke both returned available.
- Named remaining live step: driving the steering PANE in live mode needs
  a seeded Profile G task/goal; this stack's Profile G state is empty, so
  the pane drive could not run. The invocation path is unit-proved
  (`check_fix2.mjs`) and the gateway's typed behavior for confirmed
  submissions is proved live by the console's error set design (the
  capability is deliberately unmapped gateway-side).

### Suite re-runs

- Affected vitest batch 1 (desktop client, prompt steering, console
  gateway): **3 files, 17 tests, all passed**.
- Affected vitest batch 2 (ORB/IDL handoffs, tool gateway, supervisor
  boundary): **40 passed / 1 failed** — the failure is SVD-098's stale
  `supervisor_packet_count: 11` expectation vs the TS contract's 26
  capabilities (contract map B9; its inputs are untouched by audit3;
  app-side counts match exactly).
- Python integration suite (`python -m pytest tests/integration -q`):
  **528 passed / 29 skipped / 0 failed** (677.19 s under load ~9–10) —
  identical to the gap-closure baseline; no regressions. Log:
  `visual_check/fv_state/audit3/integration-suite.log`.

### Changed files (audit3, all uncommitted)

Product code (swissknife):
- `web/js/apps/agent-supervisor.js` (fixes 1, 2, 4)
- `web/js/core/mcp-plus-plus-desktop-client.js` (fix 3)
- `web/js/main-simple.js` (fixes 5, 6)

Docs (superproject):
- `BROKEN_CONTRACT_MAP.md` (P16; R6–R10; B8–B10; §4 cross-refs; §5 A3 fix table; §6)
- `visual_check/FEATURE_MATRIX.md` (F-14; screenshot index fv-14…fv-17)
- `SWISSKNIFE_FIX_NOTES.md` (this section)

Evidence (superproject, `visual_check/fv_state/audit3/`):
- `check_fix1.mjs`, `check_fix2.mjs`, `check_fix3.mjs`, `check_fix4.mjs`
- `classify_trace.mjs`, `trace-table.json`, `TRACE_TABLE.md`
- `live_probe.mjs`, `live_probe2.mjs`, `live_probe3.mjs`,
  `live-probe-results.json`, `live-probe2-results.json`,
  `live-probe3-results.json`, `bring-up.log`, `datasets-dashboard.log`,
  `live-probe-stdout.log`, `live-probe2-stdout.log`, `PROGRESS.md`
- Screenshots: `visual_check/fv-14-supervisor-console-audit3.png`,
  `fv-15-datasets-browser-audit3.png`, `fv-16-accelerate-panel-audit3.png`,
  `fv-17-supervisor-console-audit3-warm.png`

## Steering-route build (2026-10-14 — Benjamin: "build the steering adapter route")

Closes the confirmed-steering half of B10: the route from the Agent
Supervisor console to the ipfs_accelerate_py facade's `Supervisor.steer`
now exists and dispatches genuinely end-to-end. All changes UNCOMMITTED.

### Why the route has this shape (investigation, all live-verified)

- The backend feature and its MCP publication already exist:
  `agent_supervisor_steer` and siblings in
  `external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/agent_supervisor_tools/prompt_entrypoints.py`
  (ASE3-011) dispatch to the production facade. What was missing was
  transport + session hosting, in three places:
  1. The upstream FastAPI server (`fastapi_service.create_fastapi_app`)
     registers only `/healthz` and `POST /mcp/policy/evaluate`; the
     `/mcp/{path}` catch-all is the Profile G REST dispatcher and shadows
     the mounted MCP tool app (live: `GET :9000/mcp/tools` → 404), so no
     `agent_supervisor_*` tool is HTTP-reachable and the accelerate
     adapter's upstream tool catalog is empty.
  2. The prompt-lifecycle tools resolve their Supervisor through the
     embedder hook `configure_prompt_lifecycle_supervisor(...)`; nothing
     in the shipped server calls it, so each call would open a fresh
     `Supervisor.open()` whose run registry is empty (open() never
     rehydrates runs) — cross-call steering is impossible without a
     hosted long-lived session.
  3. The desktop gateway mapped no steering capability at all.
- The production composition is activatable exactly one way in this
  workspace: `Supervisor.open()` requires
  `config/agent_supervisor_prompt_only_self_improvement_v3_scheduler.json`
  under the repository root with the ASE3-026 activation completed —
  present only in the ipfs_accelerate checkout (live probe:
  `Supervisor.open(repository=<lift_coding>)` → SupervisorConfigurationError;
  `Supervisor.open(repository=<external/ipfs_accelerate>)` → succeeds).

### Changes (3 files, swissknife only; no backend repo touched)

- `scripts/mcpplusplus-supervisor-steering.cjs` (new): persistent Python
  worker bridge in the Profile G bridges' JSON-lines pattern. The worker
  opens ONE production Supervisor session for the server-configured
  repository (env `IPFS_ACCELERATE_AGENT_REPOSITORY`, default the sibling
  `external/ipfs_accelerate` checkout — never client-supplied), injects
  it via `configure_prompt_lifecycle_supervisor`, seeds the session's
  run through the facade's own `Supervisor.run()` (env
  `IPFS_ACCELERATE_SUPERVISOR_SEED_PROMPT` or a default backlog prompt),
  and dispatches the backend's own `agent_supervisor_steer` tool
  function plus a same-session `agent_supervisor_status` read-back.
  Session state and typed errors are returned verbatim — fail-closed,
  nothing fabricated.
- `scripts/all-tools-evidence-lib.cjs`: the accelerate compat adapter
  answers JSON-RPC `agent_supervisor.prompt_steering.request` through
  the bridge (warmed at listen); bridge failure → JSON-RPC error with
  the backend's real message.
- `web/js/core/mcp-plus-plus-desktop-client.js`:
  `createSupervisorGateway` gains `invokeSupervisorPromptSteering` —
  dry runs return the same typed `capability_unavailable` result as
  before, so the console's audit3 R7 local preview engages identically
  and the backend is never called for a preview; a confirmed submission
  without the console's confirmation token is denied at the gateway by
  the shared `supervisorGovernedWriteDenial` (the audit3 governed-write
  layer); a confirmed submission RPCs the adapter route and maps the
  facade observation into the governed-acceptance shape, its receipt
  CID being the backend's own `steering_prompt_cid`; backend failure
  surfaces as `server_unavailable` with the verbatim cause — never as
  `capability_unavailable`, so a confirmed failure can never be masked
  by the local preview. The console app itself is unchanged.

### Live proof (real stack; evidence `visual_check/fv_state/steering_route/`)

- Adapter hop (`adapter-steer-probe.json`): the bridge session is OPEN
  against the production composition — `open: true`, composition CID
  `baguqeerauqzq7qsd5l23zxfasd7it6rhxabq747agtnelhkmqnbcgfg5tm3a` —
  and the dispatch returns the tool envelope with the session record.
- Gateway hop (`check_gateway.mjs`): dry run →
  `unavailable/capability_unavailable`; unconfirmed →
  `denied/confirmation_required`; confirmed → dispatched,
  `server_unavailable` carrying the backend's verbatim error.
- Browser hop (`drive_console.mjs`, `drive_confirmed.mjs`; screenshots
  `fv-18`, `fv-19`): the console loads live (health available, snapshot
  genuinely empty), the steering pane renders its planned MCP action
  `agent_supervisor.prompt_steering.request`; through the page's own
  gateway and the console's `invokeCapability`, the dry run produces the
  local preview (receipt `rcpt-prompt-steering-d0d1923a`) and the
  confirmed submission surfaces the backend's verbatim boundary as
  `server_unavailable`. (One transient: the first in-browser confirmed
  call exceeded the client timeout under VM load; the warm re-run
  returns the boundary message — mediator path measured at 80 ms.)

### The typed remainder (exact missing pieces; no simulation)

1. **Run creation.** `Supervisor.run()` → `_run_from_prompt` imports
   `prompt/plan_create_service.py` → `analysis/planning_analysis_factory.py`
   → `ipfs_datasets_py.logic.formalization.autoencoder.source_screening`,
   which exists in neither datasets checkout here (pinned submodule or
   `~/workspace/ipfs_datasets_py`): cross-repo pin skew in the datasets
   logic layer. Until the datasets pin gains
   `logic/formalization/autoencoder/source_screening.py`, the hosted
   session has no run to steer and the route returns the backend's
   typed `SupervisorRunUnavailable` verbatim. The moment the module
   exists, the unchanged route executes: the bridge seeds its run at
   startup, `agent_supervisor_steer` returns the observation, and the
   gateway issues the acceptance receipt from its
   `steering_prompt_cid`. Note the facade's own semantics, by design:
   a steer is an admitted intent record (`effect_applied: False`,
   "no policy widening") consumed by the supervisor's admitted
   workflow machinery — the route serves exactly that contract.
2. **Console target seeding.** The steering pane's targets come from
   the Profile G snapshot. A complete goal→decompose→select→task seed
   chain was built and locally validated with the backend's own
   `GoalPlanValidator` (`fv_state/steering_route/seed_profile_g.py`;
   CIDs in `seed_profile_g.out`), but every Profile G service instance
   in this stack is constructed without authority/policy validators,
   so mutations fail closed with `G_AUTHORITY_DENIED`
   ("Network deployments must replace these validators using
   configure_profile_g_service before advertising the profile" — no
   bootstrap in this stack does). Configuring validators is a
   deployment decision outside this build; the seed script runs
   unchanged once one is made.
3. `supervisor.task-control.request` remains unrouted (unchanged;
   this build was prompt-steering only).

### Suites
- audit3 `check_fix2.mjs`: PASSED (console preview/typed logic intact).
- vitest batch 1 (browser-desktop-client, agent-supervisor-prompt-steering,
  agent-supervisor-console-gateway): 17/17 passed — baseline held.
- vitest batch 2 surface (ORB/IDL handoff, all-app tool gateway,
  supervisor boundary, live gateway): only failure is the pre-existing
  B9 SVD-098 stale packet-count expectation — unchanged, inputs untouched.
- Python integration suite: **528 passed / 29 skipped / 0 failed**
  (283.91 s) — the 528/29/0 baseline held exactly.

## Datasets pin advance + steering completion attempt (2026-10-14 — Benjamin: "Advance the datasets pin and finish it end-to-end")

### Pin advance: external/ipfs_datasets 8e67389b3 → f4a823231ad52c9252504810a1b00ed4738346b6
- **Old pin:** local HEAD `8e67389b3e92db5b5e87c5c1ac577426a5abfc45`
  (pin `721773d27` + the R4 solver commit; the pushed upstream form of
  that commit is `d18fc9306`). **New pin:** `f4a823231ad52c9252504810a1b00ed4738346b6`,
  the live `ipfs_datasets_py` main tip at advance start (ls-remote-verified;
  `d18fc9306` verified an ancestor, so the advance loses nothing).
  Superproject records the move as an UNSTAGED gitlink change, per
  instructions; nothing committed or pushed in any repo.
- **Step 1 (import path):** the steering bridge worker's own environment
  (cwd = superproject root, lift_coding `.venv` python,
  PYTHONPATH = external/ipfs_kit : external/ipfs_datasets :
  external/ipfs_accelerate, as constructed in
  `mcpplusplus-supervisor-steering.cjs`) resolves `ipfs_datasets_py` to
  the superproject's `external/ipfs_datasets` copy — the pin advanced is
  the right lever; pre-advance it reproduced
  `ModuleNotFoundError: No module named 'ipfs_datasets_py.logic.formalization.autoencoder'`.
- **Preservation:** the one worktree modification — the czechia
  legal_scrapers `normalize.py`, sha256
  `e12ba1297aa245c74ddc4b9b4eb61478dac1e784d8ce072d18176ad6a5276d71` —
  was copied to `visual_check/fv_state/pin_advance/normalize_preserved.py`
  before the move (sha256 verified equal) and restored byte-identically
  after; the path exists at the new pin with an identical committed blob
  at both pins. Post-advance `git update-index --refresh` reported
  exactly one path "needs update" (normalize.py), and
  `git status --porcelain` is exactly one line (` M .../normalize.py`).
- **How the checkout landed (the plain routes all failed on this egress):**
  a plain detached checkout issued one 9,523-object promisor batch over
  SSH and stalled mid-pack; chunked pathspec checkouts (219 chunks) then
  proved the lazy-fetch path is round-trip-bound through the proxy
  (32/219 banked in pass 1; HTTP/2 CANCEL errors → repo config
  `http.version=HTTP/1.1` + stored HTTPS origin for the duration, both
  reverted after) and a VM reboot killed a driver mid-pass (resumable
  chunk bookkeeping under `fv_state/pin_advance/`). The bulk bytes were
  finally moved as ONE resumable codeload tarball of the tip tree
  (3,428,060,983 bytes in a single unbroken curl stream, `gzip -t` OK),
  extracted over the worktree (0 errors), then `git read-tree <tip>`,
  a `--no-renames` stale-file pass (exactly 13 old-pin-only files
  removed; rename detection left off deliberately — it lazy-fetches
  blobs for similarity), and `git update-ref --no-deref HEAD <tip>`.
  Clone config restored (origin = SSH, `http.version` unset; promisor
  `blob:none` untouched).
- **Object store:** the worktree is 100% status-verified; of 26,687
  unique tip-tree blobs, 17,918 (67.1%) are in the local object store
  and 8,769 remain promisor-fetchable on demand. A bounded bonus
  backfill of the missing list streamed to its 1,500 s cap without its
  single pack finishing index-pack (rc=124, census unchanged).
- **LFS note:** this clone has no `filter.lfs.smudge` configured and
  git-lfs is not installed, so the one LFS subtree
  (`processors/legal_scrapers/international/harvested/`, binary
  extensions) sits in the worktree as pointer files — exactly what a
  native checkout under this clone's configuration produces.

### Suite re-baselines at the new pin (old → new)
- datasets `tests/unit/logic/ui_ux_ir/`: **285 passed / 1 failed →
  361 passed / 1 failed.** +76 tests, all passing (upstream added tests
  between the pins). The failure is B3 again, identical mechanism
  (adapter-note test ancestor-searches for the sibling accelerate
  `data/…` path — checkout-layout, typed). Environment note: the suite
  needs the three-tree PYTHONPATH the baseline runs used; without it,
  collection fails because the datasets tree's uninitialized
  `ipfs_accelerate_py` gitlink directory shadows the real package as a
  namespace package (the module exists in the accelerate checkout).
  `test_solver.py::test_solver_is_deterministic`: **1 passed** (the R4
  fix is in the new pin's ancestry). `test_mcp_idl_identity_contract.py`:
  33 → 32 tests (upstream revised the file between pins), all pass.
- Superproject integration suite: **528 passed / 29 skipped / 0 failed**
  (254.02 s) — identical to the old-pin baseline; no delta.
- Steering vitest batch (browser-desktop-client,
  agent-supervisor-prompt-steering, agent-supervisor-console-gateway):
  **17/17** — identical to baseline.

### Steering at the new pin — the boundary moved one layer deeper
Stack restarted via `fv_state/bring-up.sh` + datasets dashboard :8899
(all six ports UP, including the :9000 upstream that was down in the
steering pass). The steering bridge's session opens live (composition
CID `baguqeerauqzq7qsd5l23zxfasd7it6rhxabq747agtnelhkmqnbcgfg5tm3a`)
and the seed `Supervisor.run()` — the step the pin advance was for —
now gets PAST the datasets analysis import (that boundary is resolved:
`source_screening` on disk in the pinned submodule and importable under
the bridge's own environment) and ~19 s into plan construction, where
it fails with a new typed error: **`PlanRevisionPathError: scope_paths
must be a relative repository path`**. Root cause, code-verified
(full traceback in `fv_state/pin_advance/probe_seed.out`):
`plan_create_service.plan_create_request_from_workflow` projects
`scope_paths` from the scan directory relative to the repository root;
the facade's `_scan_directory_for_repository` returns the repository
ROOT when the repo has no `pkg/` directory (the ipfs_accelerate
checkout has none; the helper's docstring says "Scanning the repository
root is valid"), projecting scope `"."` — and
`planning/plan_revision_contracts._relative_path` explicitly rejects
`"."` and `""`. An internal inconsistency in ipfs_accelerate_py,
independent of the datasets pin. It was not worked around: editing the
facade/contracts is a backend fix outside this pass's authority, and
creating a `pkg/` directory in the accelerate tree would be a
repo-tree change that also makes the seed scan vacuous.
- **Governance re-proved at every hop at the new pin** (unchanged
  `fv_state/steering_route/check_gateway.mjs`): dry run →
  `unavailable/capability_unavailable` (console local preview engages —
  in-browser preview receipt `rcpt-prompt-steering-7a6205d4`); unconfirmed
  → `denied/confirmation_required`; confirmed → dispatched through the
  route, surfacing `server_unavailable` with the verbatim new cause —
  never masked, never simulated. (The check script exits 1 only because
  its hard-coded alternative expectation names the OLD autoencoder
  cause.) Adapter session snapshots before/after the attempts are
  byte-identical: no run exists, nothing was mutated, no receipt
  fabricated. Playwright drive: `fv-20` (steering pane, live console in
  its honest degraded/empty state, "No target selected"),
  `fv-21` (pane after the confirmed attempt), `fv-22` (console health);
  results in `fv_state/pin_advance/drive-results.json`.
- **Not exercised, deliberately:** the `configure_profile_g_service`
  validator bootstrap (local-stack-only, as briefed). Its purpose is
  letting the console pane target a seeded supervisor run; targeting is
  downstream of run creation, which is what is blocked. It remains the
  next step after the facade scope defect is fixed, together with the
  already-validated `seed_profile_g.py`.
- **Remaining chain to a real steering receipt, in order:** (1) an
  ipfs_accelerate_py fix for the scope projection/contract mismatch
  (Benjamin's call — a backend source change); (2) bridge seed succeeds
  → confirmed steer returns the backend's `steering_prompt_cid`
  acceptance through the unchanged route; (3) optional Profile G
  validator bootstrap + `seed_profile_g.py` for pane-level targeting.
  `supervisor.task-control.request` remains unrouted (unchanged).

All changes UNCOMMITTED per instructions. Evidence directory:
`visual_check/fv_state/pin_advance/` (PROGRESS.md, probes, suite logs,
drive results, preservation + census artifacts). Contract map P17/B10
and feature matrix F-15 updated.


---

## Finisher: plan-scope fix + scanner-identity fix; steering terminates at the designed nested-repository policy (2026-10-14)

Scope: Benjamin's "Advance the datasets pin and finish it end-to-end" —
the pin advance (previous section) left run creation blocked at
`PlanRevisionPathError: scope_paths must be a relative repository path`.
All changes UNCOMMITTED; no push.

### Defect 1 — plan-scope projection (the assigned defect)

Chain: bridge seed → `Supervisor.run()` → `facade._run_from_prompt` →
`plan_create_service.plan_create_request_from_workflow` →
`PlanCreateRequest.__post_init__` → `_paths` →
`plan_revision_contracts._relative_path` rejects the projected
`scope_paths=(".",)`.

Layer decision (fix the DERIVATION, not the contract): both canonical
contract layers reject root-as-value by design
(`plan_revision_contracts._relative_path` rejects `"."`; its sibling
`_absolute_path` explicitly rejects the filesystem root;
`prompt_workflow._relative_path` likewise). No test or doc admits `"."`
as a scope value (the fail-closed contracts test pins `../escape`,
absolute, and relative-`repository_root` rejections only). Boundary
translators elsewhere resolve the scan-layer `"."` sentinel rather than
passing it through (`prompt_goal_planner.py`: substitutes output paths
when the scan scope is `"."`). The contracts' representation of an
unnarrowed whole-repository scope is the EMPTY tuple: `_paths` imposes
no non-empty requirement, `PlanCreateRequest.from_dict` defaults
missing scope to `()`, production + test code construct
`scope_paths=()`, and downstream service code treats empty scope as
root scope via explicit fallbacks. The tested projection shape is a
package-relative path (service test: root `/workspace/plan-create`,
directory `…/ipfs_accelerate_py` → scope `ipfs_accelerate_py`); the
directory==root case was simply never exercised.

Fix (`external/ipfs_accelerate`, `prompt/plan_create_service.py`,
+6/−1): in `plan_create_request_from_workflow`, the derived scan scope
is translated where the projected `scope_paths` is formed — `"."`/`""`
→ `()` (`projected_scope_paths`), with a comment naming the boundary.
Explicit caller-supplied `scope_paths` untouched (the other production
caller always passes explicit scope); `_relative_path`'s guards
unchanged; no `pkg/` directory created; no bridge/seed special-casing.

### Defect 2 — scanner identity seam (found by the finisher probe)

With defect 1 fixed, the seed advanced into `preview()` and the real
scanner rejected the request: `RepositoryAllowlistError: request
allowlist identity does not match explicit allowlist`. Cause:
`observe_production_bindings` stamps the workflow request with ad-hoc
observed-scheme identities (`cid_for_dag_json` over
`observed-allowlist@1` / `observed-repository-root@1`+head_tree),
while the scanner's `_resolve_request` and the service's
`_validate_scan` recompute and demand the scanner's canonical
identities (`repository-allowlist@1` / `resolved-repository-root@1`,
sha256-digest form). The two schemes can never match, for any root —
the facade path was dead at both checks (the allowlist check fires
first; the root-cid check is next). Deciding evidence: the request is
a prompt/scanner contract — the scanner's own tests construct requests
with `allowlist.allowlist_cid` from a canonical `RepositoryAllowlist`;
the observed schemes appear exactly once in the codebase and have no
other consumer; the conformance tests assert only presence of the
observation identities (and the passing `run()` tests inject a stub
scanner, which is why the seam was never exercised end-to-end).

Fix (`entrypoints/facade.py`, +17/−2): at the request-construction
boundary in `_run_from_prompt`, compute the request's
`repository_root_cid` / `allowlist_cid` via
`prompt_directory_scanner.repository_root_cid` /
`repository_allowlist_cid`. The observation itself is untouched —
repository_id, state roots, and status displays keep the observed
domain. Downward import only (entrypoints → prompt); the pre-existing
upward-import audit failure is byte-identical before/after (20 items).

### Terminal boundary — designed policy, typed (not fixed)

With both fixes, run creation passes plan construction and both
identity checks and reaches the real scan, which raises
`NestedRepositoryError: nested repository or submodule is forbidden at
'docs/fastmcp'`. `_git_entries` rejects any gitlink in HEAD
unconditionally; the error is test-pinned by design ("A nested Git
repository makes the requested source closure ambiguous").
ipfs_accelerate_py's HEAD contains 10 tracked submodules
(docs/fastmcp, docs/mcp-python-sdk, ipfs_accelerate_py/mcplusplus,
ipfs_datasets_py, ipfs_kit_py, ipfs_model_manager_py,
ipfs_transformers_py, test/doc-builder, test/huggingface_doc_builder,
test/huggingface_transformers), and it is the only repository on this
machine with an activated production composition (ASE3-026) — no
alternative honest seed target exists. Closing this means a
backend/deployment decision (supervise a submodule-free repository, or
a sanctioned nested-repo policy in the backend); weakening the
fail-closed source-closure guard or restructuring the backend repo was
deliberately NOT improvised. The Profile G validator bootstrap remains
unexercised: pane targeting is downstream of run creation.

### Tests (before → after; fully unsealed re-runs)

The accelerate repo has a bespoke AST-seal pytest plugin
(`ipfs_accelerate_py.testing.pytest_ast_seal`): a test is skipped when
every file in its AST import closure matches a previously-passed seal.
After-numbers below come from runs against a FRESH seal store
(`IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB` pointed at a new file), so every
test genuinely re-executed. Test env: the stack's three-tree layout
(pinned datasets pre-resolved) via
`visual_check/fv_state/pin_advance/run_api_tests.py` — naive runs
resolve `ipfs_datasets_py` to the accelerate repo's vendored in-root
clone (older pin) and fail collection; an environment property, not
the defect. Note: /tmp is a 512 MB tmpfs that pytest's scratch filled
mid-run once (Errno 28); re-runs used `TMPDIR=~/.pytest_tmp` (roomy,
outside any git worktree — fixture repos must not nest inside one).

- Plan set (7 files: plan_revision_contracts, plan_create_service,
  live_root_observation, semantic_input_identity, plan_revision_store,
  lgswf_plan_revision, external_plan_revision): 143 passed →
  **143 passed, 0 failed**.
- Facade set (6 files: prompt_v3_python_api,
  prompt_only_v3_conformance, entrypoint_package,
  supervisor_planning_composition, repository_plan_preview,
  finite_integer_plan_preview): 82 passed / 2 failed / 41 errors →
  **82 passed / 2 failed / 41 errors** — failures identical
  (duckdb-connect audit; upward-import audit, same 20 violations) and
  the 41 errors are the finite-integer file's pre-existing
  "native tools are required for qualification" environment errors.
- Superproject integration (`python -m pytest tests/integration -q`):
  **528 passed / 29 skipped / 0 failed** (baseline identical).
- Steering vitest batch 1 (desktop client, prompt steering, console
  gateway): **17/17**.

### Live proof (stack restarted on the fixed code; dashboard :8899 up)

- Seed probe (`pin_advance/probe_seed.py`, replicates the bridge seed):
  before fixes — PlanRevisionPathError (`probe_seed.out`, pin-advance
  pass); after fix 1 — RepositoryAllowlistError
  (`probe_seed_fixed.out`); after fix 2 — NestedRepositoryError at the
  real scan (`probe_seed_fixed2.out`).
- Adapter (`pin_advance/adapter_probe.py`): two identical confirmed
  dispatches → `SupervisorRunUnavailable`, session `run_id: null`,
  `run_error` = the verbatim NestedRepositoryError; the two session
  snapshots are byte-identical (fail-closed, composition CID
  `baguqeerauqzq7qsd5l23zxfasd7it6rhxabq747agtnelhkmqnbcgfg5tm3a`
  unchanged, nothing mutated, no receipt fabricated)
  (`adapter-steer-1.json`, `adapter-steer-2.json`).
- Gateway (`steering_route/check_gateway.mjs`, expectation updated to
  the current verbatim cause; dry-run/unconfirmed assertions intact):
  **GATEWAY CHECK PASSED** — dry run typed `capability_unavailable`,
  unconfirmed `denied/confirmation_required`, confirmed dispatched →
  `server_unavailable` with the verbatim cause
  (`pin_advance/check_gateway.out`).
- Browser console (Playwright): dry run → local preview receipt
  `rcpt-prompt-steering-9eb1272c`; confirmed → `server_unavailable`
  with the verbatim NestedRepositoryError through the console's own
  invocation path (`drive-results-finisher.json`,
  `drive-confirmed-finisher.json`). The full drive's confirmed calls
  initially returned the gateway's 8 s RPC timeout under test-suite
  load; the focused re-drive on the idle stack returned the verbatim
  cause. Screenshots fv-23…fv-26.

### Still typed

- `supervisor.task-control.request`: no route (unchanged; out of this
  build's scope).
- Profile G validator configuration (`configure_profile_g_service`):
  a deployment decision; the pane's target list stays empty until a
  run exists and validators are configured.
- Steering execution itself: terminates at the backend's designed
  nested-repository scanner policy until the supervisor is deployed
  against a submodule-free repository (backend/deployment decision).

Evidence: `visual_check/fv_state/pin_advance/` (PROGRESS.md finisher
appendix, probes, suite logs, drive results). Contract map P17/B10 and
feature matrix F-15 updated. All changes UNCOMMITTED.

## Audit4 verification + truthfulness fixes (2026-10-15)

Re-verification pass on the current tree (steering route + datasets pin f4a82323 + two accelerate
seam fixes, all uncommitted). Suites: datasets ui_ux_ir 361 passed / 1 failed (known B3);
solver determinism 1 passed; mcp_idl_identity_contract 32 passed; superproject integration
528 passed / 29 skipped / 0 failed; steering vitest batch 17/17 (also after the fixes below);
accelerate plan set 143 passed / 0 failed; accelerate facade set 82 passed / 2 failed / 41 errors
(both failures + all errors pre-existing/environmental, identical to baseline).
GUI↔backend gap scan: inventory re-run = 45 apps / 1,401 controls, IDENTICAL to
audit3 — zero new controls; R-f/R-g fixes hold (datasets-browser and accelerate-panel hardcoded
CIDs and fixture receipts are gone: 8→0 / 4→0 CIDs, 7→0 / 7→0 receipts).

### Fix A4-1 — stale "no steering route" comment (R-h)

### Fix A4-1 — stale "no steering route" comment (R-h)
`swissknife/web/js/apps/agent-supervisor.js`, `withLocalSteeringPreview`: the comment still said
"the mediated gateway maps no prompt-steering route (a genuine backend gap)". The finisher built
that route (console → gateway → accelerate adapter → Python bridge → production `Supervisor.steer`),
so the comment was rewritten to describe the current architecture. Comment-only; behavior unchanged.

### Fix A4-2 — honest Mode badge for the standalone local preview (R-i)
`swissknife/web/js/apps/agent-supervisor.js`, steering result pane: previously a confirmed steering
submission served by the no-gateway standalone fallback rendered `Mode: confirmed` next to a
locally-computed `rcpt-prompt-steering-*` receipt with no local-preview indication. The badge now
reads `dry-run (local preview)` for dry runs and `confirmed — local preview, no backend call` for
confirmed submissions served by the standalone fallback (detected by the `rcpt-prompt-steering-`
receipt prefix); gateway-path confirmed steering still renders `confirmed`. No test asserted the
old label; steering vitest batch still 17/17 after the change.

### Fix A4-3 — "Evidence draft" markers on the VDA evidence sections (R-j)
11 app files under `swissknife/web/js/apps/` (calendar, neural-network-designer, clock, peertube,
notes, p2p-chat-unified, friends-list, image-viewer, media-player, p2p-chat, mcp-plus-plus-explorer):
each SVD evidence section header now carries `Evidence draft — CIDs, receipts and metrics shown are
fixture references for design verification.` This closes the last fabricated-claim class found by the
audit4 scan: fixture CIDs/receipts/metrics (e.g. calendar's `bafycalg035eventartifact`, media-player's
`gateway RTT 42 ms`) rendered with no fixture marking, on cards whose buttons only update local state.
Additive text only; SVD evidence markers and existing copy untouched; the e2e layout spec asserts
layout (overflow/overlap/clipping), not text content. strudel-ai-daw skipped — its section already
declares "tracked in one local session". All 12 edited JS files parse clean (esbuild).

### Deliberately not changed
- The scanner's `NestedRepositoryError` guard: designed, test-pinned policy; the nested-repo
  deployment fork is Benjamin's decision. The steering route now terminates there fail-closed with the
  verbatim backend error surfaced — never masked, never weakened.
- The 6 typed-unavailable supervisor capabilities and accelerate Cancel: re-verified zero backend
  implementations at the current pins — correctly typed, not gaps.
- Wiring the 12 VDA evidence cards to live kit artifact routes (receipts.persist → artifacts PUT etc.)
  would be the deeper fix for R-j; the evidence-draft markers are the honest, low-blast-radius close for
  this pass. Full rewiring remains future work if Benjamin wants it.
- `external/ipfs_kit` gitlink delta (recorded 40c98c71b9, checkout a9b98bea — 2026-09-28 setup residue)
  and accelerate's nested `ipfs_datasets_py`/`ipfs_kit_py` deltas: pre-existing, untouched, flagged in the
  contract map; alignment/commit is Benjamin's call.

All changes UNCOMMITTED; nothing pushed. Evidence: `~/workspace/goals/lift-coding-swissknife-gui-integration/hidden_files/audit4_*`.
