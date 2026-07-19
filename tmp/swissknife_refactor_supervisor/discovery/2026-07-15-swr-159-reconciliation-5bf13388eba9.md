# SWR-159 Reconciliation Guardrail

Date: 2026-07-15
Fingerprint: 5bf13388eba91d25d3070c943b3eb31667d03a31
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 3
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-implementation-swr-153-attempt-3-1784139447-73b12ce558fa-352ffe52b52c` at `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-153-attempt-3-1784139447`
  - Conflict paths:
    - `tree.`
- `rescue/worktree/rescue-worktree-implementation-swr-154-attempt-3-1784135827-0ea8f6d9eb5d-80b9f0ca51a0` at `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-154-attempt-3-1784135827`
  - Conflict paths:
    - `swissknife`
- `rescue/worktree/rescue-worktree-implementation-swr-154-attempt-3-1784136200-49f676332cd0-aa57f0b9d757` at `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-154-attempt-3-1784136200`
  - Conflict paths:
    - `swissknife`

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

Work surface: `3` candidates, `3` sampled records.

### Suggested Actions

- `bundle_preflight_conflicts_by_path`: group blocked branches by shared conflict paths before resolving individual branches
- `resolve_markdown_and_discovery_conflicts_deterministically`: use deterministic append-only markdown/objective/todo merge repair where conflict paths are documentation or discovery files
- `resolve_code_or_submodule_conflicts_in_isolated_worktree`: stage conflicts in a temporary reconciliation worktree or invoke the configured LLM resolver before mutating main
- `rerun_worktree_reconciliation`: rerun reconcile_backlogged_worktrees and confirm preflight_blocked_count decreases

### Safety Constraints

- Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.
- Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.
- Keep todo, objective, discovery, and strategy files parseable after reconciliation.

### Success Signals

- `preflight_blocked_count_decreases`
- `conflict_path_count_decreases`
- `reconciled_count_increases`
- `main_checkout_dirty_becomes_false`

## Machine Readable Manifest

```json
{
  "actions": [
    {
      "action": "bundle_preflight_conflicts_by_path",
      "automation": "group blocked branches by shared conflict paths before resolving individual branches",
      "scope": "backlogged_worktrees"
    },
    {
      "action": "resolve_markdown_and_discovery_conflicts_deterministically",
      "automation": "use deterministic append-only markdown/objective/todo merge repair where conflict paths are documentation or discovery files",
      "scope": "append_only_docs"
    },
    {
      "action": "resolve_code_or_submodule_conflicts_in_isolated_worktree",
      "automation": "stage conflicts in a temporary reconciliation worktree or invoke the configured LLM resolver before mutating main",
      "scope": "code_and_gitlinks"
    },
    {
      "action": "rerun_worktree_reconciliation",
      "automation": "rerun reconcile_backlogged_worktrees and confirm preflight_blocked_count decreases",
      "scope": "backlogged_worktrees"
    }
  ],
  "candidate_count": 3,
  "conflict_path_counts": {
    "swissknife": 2,
    "tree.": 1
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "5bf13388eba91d25d3070c943b3eb31667d03a31",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-implementation-swr-153-attempt-3-1784139447-73b12ce558fa-352ffe52b52c",
    "rescue/worktree/rescue-worktree-implementation-swr-154-attempt-3-1784135827-0ea8f6d9eb5d-80b9f0ca51a0",
    "rescue/worktree/rescue-worktree-implementation-swr-154-attempt-3-1784136200-49f676332cd0-aa57f0b9d757"
  ],
  "sample_count": 3,
  "sample_status_paths": [
    "tree.",
    "swissknife"
  ],
  "sample_worktrees": [
    "/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-153-attempt-3-1784139447",
    "/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-154-attempt-3-1784135827",
    "/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure-swissknife-refactor-lane/tmp/supervisor-task-worktrees/refactor/swr-154-attempt-3-1784136200"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "swissknife",
    "tree."
  ]
}
```
