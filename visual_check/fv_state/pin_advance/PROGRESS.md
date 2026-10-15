# Pin advance + steering end-to-end — progress (2026-10-14)

Task: advance external/ipfs_datasets pin to live ipfs_datasets_py main and
finish the MCP++ steering route end-to-end (Benjamin approved explicitly).
All changes UNCOMMITTED; no push; superproject gitlink change unstaged.

## Start state (verified 2026-10-14, fresh commands)
- Live ipfs_datasets_py main tip (ls-remote at start): f4a823231ad52c9252504810a1b00ed4738346b6
  (advances constantly; eb18ab0d earlier today already had autoencoder/).
- external/ipfs_datasets: HEAD == local main == 8e67389b3e92db5b5e87c5c1ac577426a5abfc45
  (= pin 721773d27 + solver commit). Worktree: exactly ONE modification,
  the preserved czechia normalize.py, sha256
  e12ba1297aa245c74ddc4b9b4eb61478dac1e784d8ce072d18176ad6a5276d71 (matches brief).
  Promisor/blobless config in place (origin SSH, blob:none filter).
  ipfs_datasets_py/logic/formalization/autoencoder/ ABSENT at pin (verified).
- swissknife: HEAD 30ade8e512093f4086ad881ac2189e65e556e97c (rebased/pushed
  equivalent of 85b65671; tree byte-identical per part-2 proof). Uncommitted
  steering set intact: M scripts/all-tools-evidence-lib.cjs,
  M web/js/core/mcp-plus-plus-desktop-client.js,
  ?? scripts/mcpplusplus-supervisor-steering.cjs.
- superproject: HEAD 0844341c (pushed audit3 tip).

## Step 1 — import path of the steering bridge worker
DONE. Replicated the bridge's exact env (cwd=superproject root, python=
.venv/bin/python, PYTHONPATH=external/ipfs_kit:external/ipfs_datasets:
external/ipfs_accelerate, as built in mcpplusplus-supervisor-steering.cjs):
  ipfs_datasets_py.__file__ = /home/hatch/workspace/lift_coding/external/ipfs_datasets/ipfs_datasets_py/__init__.py
  source_screening import FAILS (ModuleNotFoundError: ipfs_datasets_py.logic.formalization.autoencoder) — reproduces the terminal block.
=> The bridge imports the superproject's pinned submodule copy. No
discrepancy; advancing THIS pin is the right lever.

## Step 2 — preserve, then advance
PIN TARGET: f4a823231ad52c9252504810a1b00ed4738346b6 (fresh ls-remote tip at
start; blobless fetch landed attempt 1; == origin/main after fetch).
Verified in tip tree (local, tree-only):
- ipfs_datasets_py/logic/formalization/autoencoder/source_screening.py EXISTS (blob 58a1adb5)
- solver fix d18fc9306 IS an ancestor of the tip (merge-base --is-ancestor ✓)
- czechia normalize.py path EXISTS at tip; committed blob 0581461c is
  IDENTICAL at old pin and tip (the modification is purely local).
(a) Preservation: normalize.py copied to pin_advance/normalize_preserved.py;
    sha256 e12ba1297aa245c74ddc4b9b4eb61478dac1e784d8ce072d18176ad6a5276d71
    == worktree file == brief value ✓. Worktree file then reset to HEAD blob
    (clean tree) so the advance cannot trip on it; preserved bytes are
    restored over the path after checkout (brief step 2c).
(b) FIRST checkout attempt (plain `git checkout --detach <tip>`): WEDGED.
    Diagnosis (fresh process evidence): git issued ONE promisor blob batch
    (9,523 objects); the SSH upload-pack stream through the egress proxy
    stalled mid-pack at 78,921,727 bytes — tmp_pack size + mtime frozen over
    a 55 s probe, index-pack blocked on anon_pipe_read at 5 s CPU over
    ~11 min, ssh parked in poll_schedule_timeout. Killed the whole tree
    (HEAD untouched, still 8e67389b3; in-flight tmp pack discarded).
    RECOVERY (documented per brief): chunked pathspec checkout —
    `git checkout <tip> -- <chunk>` per subtree (each chunk is its own
    bounded promisor batch, so progress persists per chunk), over HTTPS
    (-c remote.origin.url=https://... per invocation; part 1 proved HTTPS
    reliable here where SSH full transfers failed 10/10; public repo,
    anonymous fetch). Failed dir chunks are split one level deeper on a
    second pass. A final `git checkout --detach <tip>` (local-only once all
    blobs are present) sets HEAD and removes pin-deleted paths.
    Driver: pin_advance/run_chunks.sh; chunk list: pin_advance/chunks.tsv
    (generated from the tip tree); log: pin_advance/chunks.log; done-set:
    pin_advance/chunks.done (resumable).

TRANSPORT FIX (during chunked checkout): the per-invocation
`-c remote.origin.url=https://...` did NOT propagate to promisor lazy-fetch
children (observed: fetch child still on ssh, parked in poll). Temporarily
set the STORED remote.origin.url to
https://github.com/endomorphosis/ipfs_datasets_py.git (was
git@github.com:endomorphosis/ipfs_datasets_py.git — RESTORE at end of step 2)
and gc.auto=0 (auto-gc was firing after fetches). New chunk invocations read
config fresh, so the running driver picks HTTPS up from the next chunk on;
chunks that already failed/stalled are retried by re-running the driver
(resumable via chunks.done).

TRANSPORT FIX #2: lazy-fetch rounds over HTTPS kept dying with curl
"HTTP/2 stream 1 was not closed cleanly: CANCEL (err 8)" — the egress
proxy mangles long-lived HTTP/2 streams. Set repo config http.version=
HTTP/1.1 (read fresh by every subsequent git invocation, incl. the running
driver's later chunks). top/scripts (1,135 files, 847 under scripts/ops)
timed out twice at the 480 s chunk cap; it will be split by children in
the failure pass (pass 2: retry once at a longer cap, then split failed
dir chunks one level deeper).
Also noted: the chunk driver's first incarnation died when its exec
session was torn down mid-chunk (top/test); relaunched detached via
setsid nohup (the fv_state pattern) — it is resumable via chunks.done.

## Step 2 (continued) — strategy change to tarball bulk move
Pass 1 (pathspec chunks, 480 s cap): 32/219 chunks banked; fails only
top/scripts (x2) + top/workspace (stream stalls / HTTP/2 CANCEL through
the proxy). A VM REBOOT (~20:38 UTC, uptime reset observed) killed the
pass-2 driver mid-chunk; stale index.lock removed; supervisor-wrapper
relaunch pattern adopted. Pass 2 (<=250-file chunks): 20/1077 banked
before being superseded. Pass 3 (same remainder re-split <=600, THREE
parallel drivers with private GIT_INDEX_FILEs seeded from the real
index): all alive but pace is round-trip-bound — git lazy fetch moves
blobs in many small proxy round trips (fetch children recycle every
~10 s, micro-packs), projecting to hours for ~1,030 remaining chunks.
DECISION: move the bulk bytes as ONE resumable codeload tarball of the
tip tree (curl -C - resume loop + anti-stall speed floor), then set
index/HEAD by plumbing (read-tree + update-ref) and let `git status`
be the ground truth; repair any residue (incl. the 6 space-paths and
the LFS-pointer subtree under processors/legal_scrapers/international/
harvested/, whose nested .gitattributes puts binary extensions on LFS)
with targeted git checkouts. Verified pre-move: root .gitattributes
has no LFS (only -whitespace rules); the LFS scope is that one nested
subtree. Drivers killed by PID; no index locks.

## Step 2 — COMPLETE (checkout landed via tarball + plumbing)
- Tarball: codeload tar.gz of f4a82323 downloaded in ONE unbroken curl
  attempt: 3,428,060,983 bytes, gzip -t OK, extracted (tar rc=0, 0 errors,
  3m01s) over the worktree with --strip-components=1 --overwrite.
- Plumbing: git read-tree <tip> (real index := tip tree); stale-file pass
  (git diff --no-renames --diff-filter=D old..tip — rename detection OFF,
  it lazy-fetches blobs for similarity and had stalled the first attempt)
  removed exactly 13 old-pin-only files; git update-ref --no-deref HEAD
  <tip> (detached HEAD = f4a82323, normal submodule state).
- Preservation (2c): normalize.py bytes restored from
  normalize_preserved.py; sha256 e12ba1297aa245c74ddc4b9b4eb61478dac1e784
  d8ce072d18176ad6a5276d71 == brief value. git update-index --refresh
  (1m45s) reported exactly one path "needs update": normalize.py.
  git status --porcelain = exactly 1 line (" M .../normalize.py").
  Saved: status_after_advance.txt.
- Step 2(d): ipfs_datasets_py/logic/formalization/autoencoder/
  source_screening.py ON DISK; bridge-env import test passes
  (ipfs_datasets_py resolves to the superproject external/ipfs_datasets
  copy; source_screening imports cleanly). Step 1 finding stands
  unchanged: the bridge was always importing the pinned submodule copy.
- LFS: this clone has NO filter.lfs.smudge configured and git-lfs is not
  installed, so a native checkout here leaves the one LFS subtree
  (processors/legal_scrapers/international/harvested/, binary extensions)
  as pointer files — identical to the tarball state. Not a delta.
- Object store: of 26,687 unique tip-tree blobs, 17,918 (67.1%) present
  locally (chunk passes + incidental fetches); 8,769 remain
  promisor-fetchable on demand (worktree is 100% status-verified). One
  bounded single-pack backfill fetch of the missing list was attempted
  as a bonus (backfill.log): it streamed for the full 1,500 s cap
  (rc=124) but its single giant pack never finished index-packing on
  this loaded box, so the census is unchanged; the checkout state does
  not depend on it.
- Clone config restored: remote.origin.url back to
  git@github.com:endomorphosis/ipfs_datasets_py.git; http.version unset.
  Promisor config (blob:none) untouched.

## Step 3 — suite re-baselines at the new pin (COMPLETE)
- (i) datasets tests/unit/logic/ui_ux_ir/ (cwd=datasets tree, three-tree
  PYTHONPATH as the baseline runs used): 361 passed / 1 failed in 13.68 s.
  Old pin: 285 passed / 1 failed. Delta +76 tests, ALL passing — upstream
  added ui_ux_ir tests between the pins. The 1 failure is B3 again,
  identical mechanism (test_domain_slice adapter-note test ancestor-
  searches for the SIBLING accelerate data/ path; resolves to
  external/data/... which does not exist — checkout-layout, typed, not a
  contract break). NOTE: without the three-tree PYTHONPATH the suite
  fails collection (the datasets tree's uninitialized ipfs_accelerate_py
  gitlink dir shadows as a namespace package) — env-attributable, not
  pin-attributable; the module exists in the accelerate checkout.
  test_solver.py::test_solver_is_deterministic: 1 passed (R4 holds; the
  fix is in the pin's ancestry via d18fc9306).
  test_mcp_idl_identity_contract.py: 32 tests at the new pin (33 at the
  old pin — upstream revised the file between pins), all pass.
- (ii) superproject integration suite: 528 passed / 29 skipped / 0 failed
  in 254.02 s — IDENTICAL to the old-pin baseline. No delta.
- (iii) steering vitest batch (console-gateway, prompt-steering,
  browser-desktop-client): 17 passed / 17 — IDENTICAL to baseline.
Logs: pytest_uiuxir_newpin.log, pytest_key_tests_newpin.log,
pytest_integration_newpin.log, vitest_steering_newpin.log (this dir).

## Step 4 — steering end-to-end attempt at the new pin
Stack: bring-up.sh (9000/8014/3002/3003/3001 all UP — upstream :9000 UP
this time) + datasets dashboard :8899 UP.
(a) Bridge seed: session open=true, composition
    baguqeerauqzq7qsd5l23zxfasd7it6rhxabq747agtnelhkmqnbcgfg5tm3a, but
    run_id=null with a NEW run_error: "PlanRevisionPathError: scope_paths
    must be a relative repository path". The source_screening import —
    the pin advance's target — is FIXED (run creation now proceeds ~19 s
    into plan construction; diagnostic probe_seed.py reproduces the full
    traceback: facade._run_from_prompt -> plan_create_request_from_workflow
    -> PlanCreateRequest.__post_init__ -> _paths -> _relative_path).
    Root cause (code-verified): plan_create_service derives scope from
    directory vs repository_root; the facade passes
    _scan_directory_for_repository(root) which returns the repo ROOT when
    no pkg/ dir exists (accelerate checkout has none; the helper's own
    docstring calls root scanning "valid"), yielding scope "." — and
    plan_revision_contracts._relative_path explicitly rejects ".".
    An internal inconsistency in ipfs_accelerate_py, one layer below the
    pin skew. NOT worked around: creating pkg/ in the accelerate tree or
    editing facade/contracts is a repo change outside this brief's
    local-stack-bootstrap allowance, and an empty pkg/ would make the
    seed vacuous anyway.
(b) Gateway probe (steering_route/check_gateway.mjs, unchanged): dry-run
    unavailable/capability_unavailable; unconfirmed denied/
    confirmation_required; confirmed DISPATCHED -> unavailable/
    server_unavailable with the new verbatim cause (never masked). The
    script exits 1 only because its hard-coded alternative expectation
    names the OLD autoencoder cause. Evidence: check_gateway.out.
(c) Before/after adapter session snapshots (empty-prompt typed probe):
    byte-identical; no run exists, nothing mutated, no receipt
    fabricated. adapter-probe-before.json / adapter-probe-after.json.
(d) Playwright pane drive (pin_advance/drive_pane.mjs): console live
    (gateway installed, degraded/empty snapshot shown honestly — no
    fixtures), steering pane "No target selected" (Profile G snapshot
    empty); console-path dry run -> local preview receipt
    rcpt-prompt-steering-7a6205d4; confirmed -> server_unavailable with
    the verbatim PlanRevisionPathError. Screenshots fv-20 (pane),
    fv-21 (pane after), fv-22 (health). drive-results.json.
    The configure_profile_g_service validator bootstrap was NOT
    exercised: its purpose is letting the pane target a seeded run, and
    no run can be created until the facade scope defect is fixed —
    targeting is downstream of the actual block. Named as the exact
    remaining gap chain in the step-5 docs.


---

## FINISHER APPENDIX (2026-10-14) — scope defect fixed; second seam fixed; terminal boundary is a designed policy

Tasking: fix the plan-creation scope defect (step 4's terminal block)
and finish the steering route end-to-end. Outcome: BOTH internal
inconsistencies in the run-creation chain are fixed (uncommitted);
run creation now reaches the backend's real directory scanner, which
terminates it under a designed, test-pinned policy. The "remaining
chain" from step 5 is superseded by this appendix where they differ.

### Fix 1 — scope projection (`external/ipfs_accelerate`, plan_create_service.py +6/−1)
`plan_create_request_from_workflow` leaked the scan layer's root
sentinel "." into `PlanCreateRequest.scope_paths`, which
`plan_revision_contracts._relative_path` rejects by design (both
canonical contract layers reject root-as-value; the contracts'
unnarrowed-scope representation is the empty tuple). The projection
now emits `()` for a root scan. Deciding evidence + alternatives
weighed: see SWISSKNIFE_FIX_NOTES.md finisher section and
BROKEN_CONTRACT_MAP B10. Probe after fix 1 (`probe_seed_fixed.out`):
PlanRevisionPathError GONE; run creation advanced to the scanner
identity check.

### Fix 2 — scanner identity seam (`external/ipfs_accelerate`, entrypoints/facade.py +17/−2)
`observe_production_bindings`' ad-hoc observed-scheme identities
(`observed-allowlist@1`, `observed-repository-root@1`) can never match
the scanner's canonical identities (`repository-allowlist@1`,
`resolved-repository-root@1`) that `_resolve_request` and
`_validate_scan` recompute — the facade path was dead at both checks
for any repository. `_run_from_prompt` now computes the request's
identities via `prompt_directory_scanner.repository_allowlist_cid` /
`repository_root_cid`; the observation domain is unchanged. Probe
after fix 2 (`probe_seed_fixed2.out`): both identity checks PASS; the
scan proceeds into content scanning.

### Terminal boundary — designed, test-pinned policy (typed)
`NestedRepositoryError: nested repository or submodule is forbidden at
'docs/fastmcp'`. `_git_entries` rejects any HEAD gitlink
unconditionally (scanner test pins it; "source closure ambiguous").
The accelerate HEAD has 10 tracked submodules; it is also the only
repo on this machine with an activated composition — no alternative
seed target exists. Not an inconsistency; closing it is a
backend/deployment decision (submodule-free supervisor target or a
sanctioned nested-repo policy). NOT weakened, NOT worked around.
Profile G validator bootstrap still unexercised (targeting is
downstream of run creation).

### Tests (fresh-seal-store re-runs; runner: pin_advance/run_api_tests.py)
- Plan set (7 files): BEFORE 143 passed → AFTER 143 passed, 0 failed
  (api_tests_after_fresh.log; the repo's AST-seal plugin skips
  previously-passed closures — after2's "143 skipped" run is the seal
  working as designed, not a result).
- Facade set (6 files): BEFORE 82 passed / 2 failed / 41 errors →
  AFTER identical (api_tests_facade_after_fresh.log); the 2 failures
  (duckdb-connect audit; upward-import audit — same 20 violations) and
  41 finite-integer "native tools" errors are pre-existing/env.
- Integration (superproject): 528 passed / 29 skipped / 0 failed
  (integration-suite-finisher.log) — baseline identical.
- Steering vitest batch 1: 17/17 (vitest-batch1-finisher.log).
- Env notes: naive accelerate test runs resolve ipfs_datasets_py to
  the repo's vendored in-root clone (collection failure — environment,
  not defect); /tmp tmpfs (512 MB) filled once by pytest scratch
  (Errno 28) — re-runs used TMPDIR=~/.pytest_tmp.

### Live proof (stack restarted on fixed code; :8899 via launch_mcp_dashboard)
- adapter_probe.py → adapter-steer-1.json / adapter-steer-2.json:
  identical fail-closed sessions, run_error = verbatim
  NestedRepositoryError, composition CID unchanged.
- steering_route/check_gateway.mjs (expectation updated to the current
  verbatim cause; dry-run + unconfirmed assertions intact):
  GATEWAY CHECK PASSED (check_gateway.out, rc=0).
- Playwright: drive-results-finisher.json (dry → preview receipt
  rcpt-prompt-steering-9eb1272c; confirmed initially hit the gateway's
  8 s RPC timeout under test load) + drive-confirmed-finisher.json
  (idle-stack re-drive: confirmed → server_unavailable with the
  verbatim NestedRepositoryError through the console path).
  Screenshots fv-23, fv-24, fv-25, fv-26.

### Doc updates applied
BROKEN_CONTRACT_MAP.md (P17 verdict rewritten; B10 finisher
resolution + terminal policy; §5/§6 cross-refs corrected),
FEATURE_MATRIX.md (F-15 finisher paragraph), SWISSKNIFE_FIX_NOTES.md
(finisher section). All changes UNCOMMITTED; no push. The datasets
clone was never touched (no git run inside external/ipfs_datasets;
the preserved czechia normalize.py untouched).
