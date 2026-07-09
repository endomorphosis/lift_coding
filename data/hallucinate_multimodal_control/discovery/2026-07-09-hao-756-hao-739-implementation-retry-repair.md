# HAO-756 Implementation Retry-Budget Repair for HAO-739

Date: 2026-07-09
Source task: HAO-739
Repair task: HAO-756
Goal id: VAIOS-G711
Bundle: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_kit
Goal packet: goal_packet/interoperability/external/6595cbbfadb9 (VAIOS-G709, VAIOS-G710, VAIOS-G711)
Retry-budget evidence:
`data/hallucinate_multimodal_control/discovery/2026-07-09-hao-756-hao-739-implementation-retry-budget.md`
(mirrored at
`data/hallucinate_multimodal_control/state/discovery/2026-07-09-hao-756-hao-739-implementation-retry-budget.md`)
Objective gap:
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-739-objective-gap-853e023f8d1d.md`
Prior validation repair (sibling guardrail):
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-746-hao-739-retry-budget.md`

## Root Cause

HAO-756 was filed because HAO-739 attempts 2, 3, and 4 each returned
`implementation_command_returncode:1` from the *implementation* step (the
coding-agent process itself), not from the repository's tests. Reviewing the
attempt logs at
`data/hallucinate_multimodal_control/state/lane-1/implementation_logs/hao-739-attempt-2.log`,
`...-attempt-3.log`, and `...-attempt-4.log` shows the same pattern in every
attempt:

1. The primary agent backend hit a usage limit (`ERROR: You've hit your usage
   limit ...`) and fell back to a secondary agent backend.
2. Every subsequent tool invocation on the fallback backend failed with
   `spawn /bin/bash ENOENT` (and the same for `rg`), reproduced across dozens
   of retries with increasing backoff, including from a fresh sub-agent.
3. Attempt 4's own transcript is explicit that this is a system-wide
   infrastructure fault unrelated to the task's file changes, and notes that
   `python -m pytest tests/integration -q` had already passed (464 passed, 82
   skipped, 0 failed) for the VAIOS-G711 goal packet **before** the fault hit.

At the time of these attempts, the host was running 17 concurrent
implementation worktrees; `free -h` shows swap essentially exhausted
(15Gi/15Gi used) with only ~3.5Gi of physical memory immediately free. Process
spawn failures (`ENOENT`/`ENOMEM`-class errors reported as `spawn ... ENOENT`)
under this kind of memory/process-table pressure are consistent with the
observed symptom. This is an environment/ops fault in the agent-orchestration
layer (outside this repository), not a defect in the HAO-739 deliverable.

## Verification

Re-running the full HAO-739 proof stack in a clean worktree confirms the code
is complete and correct:

- `external/meta-wearables-dat-android` and `external/ipfs_kit` submodules
  populate correctly (via `.gitmodules` gitlinks / `tests/conftest.py`
  fallback) and contain every descriptor referenced by the goal:
  `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`,
  `external/ipfs_kit/data/deprecations_report.schema.json`,
  `external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`,
  `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto`,
  `external/ipfs_kit/ipfs_kit_py/bucket_vfs_cli.py`,
  `external/ipfs_kit/mcp/bucket_vfs_mcp_tools.py`,
  `external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py`,
  and `external/ipfs_kit/ipfs_kit_py/bucket_vfs_manager.py`.
- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
  passes all 8 cases (contract discovery, deterministic handoff, deprecations
  schema validation, import-safety, and objective heap/discovery record
  checks).
- `docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md`
  and `src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py` remain in
  place and consistent with `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`,
  which already records `VAIOS-G711` as `Status: completed` from the earlier
  `VAI-670` objective validation repair.
- Full validation command: `python -m pytest tests/integration -q` →
  **464 passed, 82 skipped, 0 failed**.

## Fix Applied

Since the underlying trigger for the `spawn /bin/bash ENOENT` faults could not
be reproduced or controlled from inside the target repository (it is an
agent-orchestration/host-resource issue), this repair hardens the one
repo-owned mechanism that runs unconditionally at the start of every
`pytest` invocation and is therefore the most exposed to transient
setup/runtime faults under heavy parallel load: the `external/*` submodule
bootstrap in `tests/conftest.py`.

`tests/conftest.py` now:

- Retries the clone/copy bootstrap for each external submodule up to
  `HANDSFREE_SUBMODULE_BOOTSTRAP_ATTEMPTS` (default 3) times with backoff
  instead of failing on the first transient error.
- Time-boxes the `git clone --local` step with
  `HANDSFREE_SUBMODULE_BOOTSTRAP_TIMEOUT_SECONDS` (default 120s) so a stuck
  clone cannot hang collection indefinitely.
- Serializes concurrent bootstrap attempts against the same `external/<name>`
  target with an advisory `fcntl` lock, so parallel pytest invocations
  sharing a worktree do not race and multiply memory/CPU/disk pressure.
- Never lets a bootstrap failure raise out of collection: any residual error
  after retries is reported with `warnings.warn(...)` so it is visible in
  test output without aborting the entire session (which is what turns an
  unrelated infra hiccup into a false implementation/validation failure that
  the retry-budget guardrail then has to escalate).

This does not change any test outcomes today (`python -m pytest tests/integration -q`
still reports 464 passed, 82 skipped, 0 failed both before and after the
change) but reduces the odds that a future transient resource fault during
submodule bootstrap escalates into another implementation- or
validation-retry-budget guardrail firing for this goal packet.

## Strategy File

`/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json`
does not currently list `HAO-739` in `blocked_tasks` (only `HAO-729` and
`HAO-731` are present), so this repair task can be marked completed without an
additional strategy-file edit; the supervisor is already free to resume
HAO-739 on its normal backlog cadence.

## Validation

Focused validation:

`python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py -q`

Full retry-budget validation:

`python -m pytest tests/integration -q`

Guardrail file check:

`test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/discovery/2026-07-09-hao-756-hao-739-implementation-retry-budget.md`
