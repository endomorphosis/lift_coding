# PGIR-125 Reconciliation Guardrail

Date: 2026-08-18
Fingerprint: 966d0ad9c6c84ee53747ba9d79f6f5590a58c1ab
Kind: dirty_backlogged_worktree
Reason: unsupported_status
Candidate count: 1
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--96e30dd9c6ca` at `/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-70626075579a-aafcace8f27e` status: ` ? ipfs_datasets_py`

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
- `resolve_unsupported_statuses`: handle deletes, renames, unmerged paths, or unusual index states with an explicit resolver pass
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
      "action": "resolve_unsupported_statuses",
      "automation": "handle deletes, renames, unmerged paths, or unusual index states with an explicit resolver pass",
      "scope": "dirty_worktrees"
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
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status",
  "fingerprint": "966d0ad9c6c84ee53747ba9d79f6f5590a58c1ab",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "unsupported_status",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--96e30dd9c6ca"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "ipfs_datasets_py"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-70626075579a-aafcace8f27e"
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
