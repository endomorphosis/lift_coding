# HAO-311 Reconciliation Guardrail

Date: 2026-06-26
Fingerprint: 94efe8549522a81110856366aa8dc8de6e615ea4
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 7
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/hao-678-attempt-10-1782427644` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-10-1782427644`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/hao-678-attempt-11-1782433436` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-11-1782433436`
  - Conflict paths:
    - `hallucinate_app`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--120c2cbed5c0` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-8-1782426388`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--b9d765930a61` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-680-attempt-1-1782423241`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/hao-680-attempt-4-1782430900` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-680-attempt-4-1782430900`
  - Conflict paths:
    - `hallucinate_app`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/hao-687-attempt-1-1782422501` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-687-attempt-1-1782422501`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/hao-698-attempt-1-1782430237` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-698-attempt-1-1782430237`
  - Conflict paths:
    - `hallucinate_app`
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

Work surface: `7` candidates, `7` sampled records.

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
  "candidate_count": 7,
  "conflict_path_counts": {
    "hallucinate_app": 3,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 4,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 5,
    "swissknife": 1
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "94efe8549522a81110856366aa8dc8de6e615ea4",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/hao-678-attempt-10-1782427644",
    "implementation/hao-678-attempt-11-1782433436",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--120c2cbed5c0",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--b9d765930a61",
    "implementation/hao-680-attempt-4-1782430900",
    "implementation/hao-687-attempt-1-1782422501",
    "implementation/hao-698-attempt-1-1782430237"
  ],
  "sample_count": 7,
  "sample_status_paths": [
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "swissknife"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-10-1782427644",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-11-1782433436",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-678-attempt-8-1782426388",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-680-attempt-1-1782423241",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-680-attempt-4-1782430900",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-687-attempt-1-1782422501",
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-698-attempt-1-1782430237"
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
    "hallucinate_app",
    "swissknife"
  ]
}
```
