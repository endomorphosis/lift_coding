# HAO-416 Merge Retry-Budget Finding: HAO-313

Date: 2026-06-12
Source task: HAO-313
Follow-up task: HAO-416
Retry budget: 3
Observed consecutive merge failures: 3

## Evidence

- Failed command: `git merge (main_checkout_dirty_conflict)`
- Attempts: 1, 1, 1
- Logs: not recorded
- Merge reason: `main_checkout_dirty_conflict`
- Dirty paths: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Branch: `implementation/hao-313-attempt-1-1780993612`
- Main worktree: `/home/barberb/lift_coding`


## Guardrail Result

The accelerator backlog refinery classified this as backlog work instead of
allowing another implementation attempt to loop on the same failure. The source
task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended for normal daemon parsing.

## Repair Resolution

- Main checkout status was clean when HAO-416 ran, so the recorded
  `main_checkout_dirty_conflict` dirty path no longer blocks merges.
- HAO-313 parent commit `6d4305db` points `external/ipfs_kit` backward from
  `55dc7f68` to `3235a54f`; its intended nested working-tree change was the
  `_find_deals_for_cid` unreadable/malformed mock deal handling in
  `archive/applied_patches/advanced_filecoin.py`.
- The intended implementation is already committed in the owning `ipfs_kit`
  submodule as `aac0f50c` (`VAI-214: Review swallowed exception path in
  external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245`) and is
  included by current parent submodule pointer `55dc7f68`.
- Correct merge resolution for HAO-313 is to keep the current `external/ipfs_kit`
  pointer at `55dc7f68` rather than applying HAO-313's stale rewind to
  `3235a54f`; this preserves the committed fix and avoids a dirty nested
  submodule state.
- `ipfs-accelerate-agent-merge-resolver` was not run because the observed
  failure reason was checkout dirtiness, not a semantic conflict, and the
  resolver command is not available in this environment's `PATH`.
