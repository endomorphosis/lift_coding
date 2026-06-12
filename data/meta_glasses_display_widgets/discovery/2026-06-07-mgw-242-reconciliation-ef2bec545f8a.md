# MGW-242 Reconciliation Guardrail

Date: 2026-06-12
Fingerprint: 75b21a909bce3504a0e2c3b1090fdd57e464764e
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 11
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/mgw-001-attempt-1-1781226554` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-001-attempt-1-1781226554`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-002-attempt-1-1781228395` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-002-attempt-1-1781228395`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `rescue/worktree/implementation-mgw-004-attempt-1-1781229018-d0226fbce6ab` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-004-attempt-1-1781229018`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `rescue/worktree/implementation-mgw-005-attempt-1-1781229784-675aa8ee06a3` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-005-attempt-1-1781229784`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-035-attempt-1-1781235219` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-035-attempt-1-1781235219`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-043-attempt-1-1781236407` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-043-attempt-1-1781236407`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-065-attempt-2-1781232555` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-065-attempt-2-1781232555`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-121-attempt-1-1780997197` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-121-attempt-1-1780997197`
  - Conflict paths:
    - `hallucinate_app`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-125-attempt-2-1780999263` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-125-attempt-2-1780999263`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/mgw-126-attempt-1-1780999750` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-126-attempt-1-1780999750`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--2d990c4ff79e` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-127-attempt-1-1781232813`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`

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

Work surface: `11` candidates, `11` sampled records.

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
  "candidate_count": 11,
  "conflict_path_counts": {
    "hallucinate_app": 1,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 8,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 9
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "75b21a909bce3504a0e2c3b1090fdd57e464764e",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/mgw-001-attempt-1-1781226554",
    "implementation/mgw-002-attempt-1-1781228395",
    "rescue/worktree/implementation-mgw-004-attempt-1-1781229018-d0226fbce6ab",
    "rescue/worktree/implementation-mgw-005-attempt-1-1781229784-675aa8ee06a3",
    "implementation/mgw-035-attempt-1-1781235219",
    "implementation/mgw-043-attempt-1-1781236407",
    "implementation/mgw-065-attempt-2-1781232555",
    "implementation/mgw-121-attempt-1-1780997197",
    "implementation/mgw-125-attempt-2-1780999263",
    "implementation/mgw-126-attempt-1-1780999750",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--2d990c4ff79e"
  ],
  "sample_count": 11,
  "sample_status_paths": [
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "hallucinate_app"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-001-attempt-1-1781226554",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-002-attempt-1-1781228395",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-004-attempt-1-1781229018",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-005-attempt-1-1781229784",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-035-attempt-1-1781235219",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-043-attempt-1-1781236407",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-065-attempt-2-1781232555",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-121-attempt-1-1780997197",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-125-attempt-2-1780999263",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-126-attempt-1-1780999750",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-127-attempt-1-1781232813"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "hallucinate_app"
  ]
}
```
