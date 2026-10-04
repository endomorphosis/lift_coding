# PGIR-121 Reconciliation Guardrail

Date: 2026-08-18
Fingerprint: e2fea239d87284c4682d9643d136eb867410380f
Kind: dirty_backlogged_worktree
Reason: submodule_gitlink_diverged
Candidate count: 1
Priority: P2
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--b322f1d6e1b7` at `/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-eba1dd201646-fffe5eab3d95` status: ` m ipfs_datasets_py`
  - Name status:
    - `M	ipfs_datasets_py`
  - Diff stat:
    - `ipfs_datasets_py | 0`
    - ` 1 file changed, 0 insertions(+), 0 deletions(-)`

## Why This Blocks Progress

The implementation supervisor can only merge clean inactive implementation
worktrees when the main checkout is safe to mutate. Dirty main checkouts and
dirty backlogged worktrees are preserved until a deliberate reconciliation task
decides whether to commit, merge, discard generated duplicates, or split
unresolved work into follow-up tasks.

## Suggested Repair

Inspect the dirty paths and sampled worktrees, resolve any real work into
reviewable commits or follow-up tasks, rerun the supervisor reconciliation pass,
and verify that either the candidate merge count decreases or the dirty
worktree cleanup skip count decreases.

## Reconciliation Plan

Work surface: `1` candidates, `1` sampled records.

### Suggested Actions

- `classify_dirty_worktree_group`: inspect sampled dirty statuses and compare against the target ref
- `preserve_or_merge_backlogged_work`: merge valuable branch work, commit preserved changes, or file follow-up tasks for unresolved work
- `rerun_cleanup_pass`: rerun cleanup_backlogged_worktrees after preserving or merging dirty worktree content

### Safety Constraints

- Do not discard dirty or untracked content unless it is proven redundant with the target ref.
- Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.
- Keep todo, objective, discovery, and strategy files parseable after reconciliation.

### Success Signals

- `candidate_count_decreases`
- `dirty_worktree_group_count_decreases`
- `main_checkout_dirty_becomes_false`
- `cleanup_or_reconciliation_pass_processes_candidates`

## Machine Readable Manifest

```json
{
  "actions": [
    {
      "action": "classify_dirty_worktree_group",
      "automation": "inspect sampled dirty statuses and compare against the target ref",
      "scope": "sampled_worktrees"
    },
    {
      "action": "preserve_or_merge_backlogged_work",
      "automation": "merge valuable branch work, commit preserved changes, or file follow-up tasks for unresolved work",
      "scope": "dirty_worktrees"
    },
    {
      "action": "rerun_cleanup_pass",
      "automation": "rerun cleanup_backlogged_worktrees after preserving or merging dirty worktree content",
      "scope": "worktree_root"
    }
  ],
  "candidate_count": 1,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:submodule_gitlink_diverged",
  "fingerprint": "e2fea239d87284c4682d9643d136eb867410380f",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "submodule_gitlink_diverged",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--b322f1d6e1b7"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "ipfs_datasets_py"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-eba1dd201646-fffe5eab3d95"
  ],
  "success_signals": [
    "candidate_count_decreases",
    "dirty_worktree_group_count_decreases",
    "main_checkout_dirty_becomes_false",
    "cleanup_or_reconciliation_pass_processes_candidates"
  ],
  "top_conflict_paths": []
}
```
