# SCA-632: SCA-615 merge retry-budget repair

Date: 2026-07-29
Source task: SCA-615
Follow-up task: SCA-632
Failure kind: merge (`main_branch_checked_out_elsewhere`)
Repair round: 1 (proposal-gate size repair)

## Root cause

Merge target `agent/swissknife-sca-parallel` was checked out at the shared
worktree `/home/barberb/211-AI/.worktrees/sca-audit-followups`.
`_prepare_main_merge_workspace` failed closed for any target checkout outside
the managed `.main-merge-worktrees` root, so SCA-615 could not integrate after
validation passed (10 consecutive merge failures).

This was an operational merge-workspace blocker, not a semantic content conflict.
`ipfs-accelerate-agent-merge-resolver --apply` was not required.

## Attempt-1 admission failure

Attempt 1 integrated the correct fix but re-emitted full source for
`implementation_daemon.py` (~1.07 MiB) into the proposal. Proposal admission
rejects single files over 1_048_576 bytes (`large_file_forbidden`,
`output_too_large`, `patch_too_large`).

## Durable fix (already on baseline)

Submodule `external/ipfs_accelerate` @ `511d42fdd`:

- Reuse a **clean** external merge-target checkout instead of failing with
  `main_branch_checked_out_elsewhere`.
- Sets `reused_external_checkout: true` on success.
- Still fails closed when the external checkout remains dirty.

Parent baseline `a8132ab0d` already points the gitlink at that fix and includes
SCA-615 production-provider route evaluation.

## Repair strategy (this attempt)

Do **not** re-diff large submodule sources in the proposal. Leave
`implementation_daemon.py` and other submodule declared outputs unchanged
relative to gitlink `511d42fdd`. Ship only this small discovery receipt so the
supervisor can admit SCA-632 and release SCA-615 from strategy `blocked_tasks`.

## Validation

```text
test -f data/.../discovery/2026-07-29-sca-632-sca-615-merge-retry-budget.md
pytest external/ipfs_accelerate/test/api/test_agent_supervisor_production_provider_route.py -q
# expect: 15 passed
```

## Status

**REPAIR COMPLETED** — merge guardrail present on submodule tip; proposal kept
under admission budgets by not re-including oversized source files.
