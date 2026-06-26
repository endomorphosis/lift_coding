# VAI-202 Reconciliation Guardrail

Date: 2026-06-26
Fingerprint: 364bd44921446da49ec5c3d17ec3d5303baa432b
Kind: dirty_backlogged_worktree
Reason: unsupported_status
Candidate count: 2
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--cc09eca52d16` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-508-attempt-1-1782422956` status: ` m swissknife`
  - Name status:
    - `M	swissknife`
  - Diff stat:
    - `swissknife | 0`
    - ` 1 file changed, 0 insertions(+), 0 deletions(-)`
- `implementation/vai-512-attempt-12-1782434708` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782434708` status: ` m hallucinate_app;  M implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md;  m swissknife; ?? data/hallucinate_multimodal_control/discovery/2026-06-26-hao-vai-512-mcp-dashboard-consumption.md; ?? data/virtual_ai_os/discovery/2026-06-26-vai-512-mcp-dashboard-consumption.md`
  - Name status:
    - `M	hallucinate_app`
    - `M	implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `M	swissknife`
  - Diff stat:
    - `hallucinate_app                                       |  0`
    - ` ...18-swissknife-meta-glasses-display-widgets.todo.md | 19 ++++++++++++++++---`
    - ` swissknife                                            |  0`
    - ` 3 files changed, 16 insertions(+), 3 deletions(-)`
  - Untracked paths:
    - `data/hallucinate_multimodal_control/discovery/2026-06-26-hao-vai-512-mcp-dashboard-consumption.md`
    - `data/virtual_ai_os/discovery/2026-06-26-vai-512-mcp-dashboard-consumption.md`

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

Work surface: `2` candidates, `2` sampled records.

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
  "candidate_count": 2,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status",
  "fingerprint": "364bd44921446da49ec5c3d17ec3d5303baa432b",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "unsupported_status",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--cc09eca52d16",
    "implementation/vai-512-attempt-12-1782434708"
  ],
  "sample_count": 2,
  "sample_status_paths": [
    "swissknife",
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-vai-512-mcp-dashboard-consumption.md",
    "data/virtual_ai_os/discovery/2026-06-26-vai-512-mcp-dashboard-consumption.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-508-attempt-1-1782422956",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782434708"
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
