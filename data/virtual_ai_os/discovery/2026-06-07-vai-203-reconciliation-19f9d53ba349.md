# VAI-203 Reconciliation Guardrail

Date: 2026-06-26
Fingerprint: 19f60bb10e8f6f0da6d81ab09be47ad5148600c4
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 5
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--aafa7f1903af` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-2-1782433690`
  - Conflict paths:
    - `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--7979f6ceb663` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433437`
  - Conflict paths:
    - `tree.`
    - `hallucinate_app`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--93342c6279a9` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782435836`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/vai-512-attempt-12-1782436353` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782436353`
  - Conflict paths:
    - `hallucinate_app`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `swissknife`
- `implementation/vai-514-attempt-1-1782427150` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-514-attempt-1-1782427150`
  - Conflict paths:
    - `hallucinate_app`
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

Work surface: `5` candidates, `5` sampled records.

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
  "candidate_count": 5,
  "conflict_path_counts": {
    "hallucinate_app": 3,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 3,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 2,
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md": 1,
    "swissknife": 2,
    "tree.": 1
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "19f60bb10e8f6f0da6d81ab09be47ad5148600c4",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--aafa7f1903af",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--7979f6ceb663",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--93342c6279a9",
    "implementation/vai-512-attempt-12-1782436353",
    "implementation/vai-514-attempt-1-1782427150"
  ],
  "sample_count": 5,
  "sample_status_paths": [
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
    "tree.",
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "swissknife"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-2-1782433690",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433437",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782435836",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782436353",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-514-attempt-1-1782427150"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "swissknife",
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
    "tree."
  ]
}
```
