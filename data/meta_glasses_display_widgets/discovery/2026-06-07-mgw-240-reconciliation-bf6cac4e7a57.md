# MGW-240 Reconciliation Guardrail

Date: 2026-06-09
Fingerprint: aa06f1c0d3d6225ea8d02248ac4b009a7746a7ce
Kind: dirty_backlogged_worktree
Reason: content_not_in_target
Candidate count: 1
Priority: P2
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/mgw-181-attempt-1-1780988528` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-181-attempt-1-1780988528` status: ` M implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
  - Name status:
    - `M	implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
  - Diff stat:
    - `.../docs/19-virtual-ai-os-submodule-integration.todo.md             | 6 +++---`
    - ` 1 file changed, 3 insertions(+), 3 deletions(-)`

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
- `compare_dirty_content_to_target`: separate real unmerged content from generated duplicates before deleting worktrees
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
      "action": "compare_dirty_content_to_target",
      "automation": "separate real unmerged content from generated duplicates before deleting worktrees",
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
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:content_not_in_target",
  "fingerprint": "aa06f1c0d3d6225ea8d02248ac4b009a7746a7ce",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "content_not_in_target",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/mgw-181-attempt-1-1780988528"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-181-attempt-1-1780988528"
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

## Resolution Evidence

Recorded during MGW-240 reconciliation on 2026-06-07.

- Live dirty already-merged MGW worktrees were classified before cleanup:
  `61` were generated-only todo/discovery/objective edits and `20` contained
  code, test, script, submodule, or tracking changes.
- The generated-only resolver touched only these path classes:
  `implementation_plan/docs/*.todo.md`,
  `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`, and
  `data/*/discovery/*.md`.
- Representative stale-generated checks:
  `implementation/mgw-125-attempt-1-1779887576` only re-added MGW-125 through
  MGW-129 backlog blocks already represented in the current task board, and
  `implementation/mgw-153-attempt-1-1779965069` had an older untracked MGW-153
  resolution while the target already contains the resolution document.
- The resolver restored `79` tracked generated paths and removed `5` untracked
  generated discovery files, leaving `61` worktrees clean for normal supervisor
  cleanup.
- Mixed/code worktrees were deliberately preserved. The remaining dirty group
  includes script, test, submodule, tracking, or objective-heap changes that
  should be reviewed separately instead of discarded.
- A fresh shared supervisor pass was run from `/home/barberb/lift_coding` with
  the worktree scan cache disabled:

```sh
python3 /home/barberb/lift_coding/scripts/meta_glasses_display_todo_supervisor.py --once --reconciliation-only --no-worktree-scan-cache --worktree-reconciliation-max-merges 0
```

- The cleanup event at `2026-06-07T08:14:27.164008+00:00` reported
  `removed_count = 61`, `dirty_worktree:content_not_in_target = 20`,
  `not_merged = 16`, `active_state_worktree = 1`, and
  `scan_cache_hit_count = 0`.
- Original guardrail candidate count: `81`.
- Current content-not-in-target blocked candidate count: `20`.
- Count decrease confirmed: `81 -> 20`.

Verification command used:

```sh
jq -r 'select(.type=="merged_worktree_cleanup") | [.timestamp, (.removed_count // 0), (.skipped_reason_counts["dirty_worktree:content_not_in_target"] // 0), (.dirty_worktree_groups.content_not_in_target.count // 0), (.scan_cache_hit_count // 0)] | @tsv' /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_supervisor_events.jsonl | tail -n 8
```
