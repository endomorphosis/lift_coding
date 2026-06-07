# MGW-241 Reconciliation Guardrail

Date: 2026-06-07
Fingerprint: 731f0bb0db091c0d6d7bbf9d8746d1f86e43646e
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

- `implementation/mgw-071-attempt-1-1779831690` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-071-attempt-1-1779831690` status: ` D external/meta-wearables-dat-android;  D swissknife`
  - Name status:
    - `D	external/meta-wearables-dat-android`
    - `D	swissknife`
  - Diff stat:
    - `external/meta-wearables-dat-android | 1 -`
    - ` swissknife                          | 1 -`
    - ` 2 files changed, 2 deletions(-)`
- `implementation/mgw-085-attempt-1-1779837810` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-085-attempt-1-1779837810` status: ` D swissknife`
  - Name status:
    - `D	swissknife`
  - Diff stat:
    - `swissknife | 1 -`
    - ` 1 file changed, 1 deletion(-)`

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

## Resolution Evidence

Recorded during MGW-241 reconciliation on 2026-06-07.

- Live worktree registration no longer includes
  `implementation/mgw-071-attempt-1-1779831690` or
  `implementation/mgw-085-attempt-1-1779837810`.
- The sampled worktree paths no longer exist on disk:
  `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-071-attempt-1-1779831690`
  and
  `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-085-attempt-1-1779837810`.
- A fresh supervisor cleanup/reconciliation pass was observed from
  `/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_supervisor_events.jsonl`.
  The latest cleanup events at `2026-06-07T07:55:06.477719+00:00` and
  `2026-06-07T07:56:22.539444+00:00` reported
  `dirty_worktree:unsupported_status = 0`.
- Original guardrail candidate count: `2`.
- Current unsupported-status blocked candidate count: `0`.
- Count decrease confirmed: `2 -> 0`.

Verification commands:

```sh
git -C /home/barberb/lift_coding worktree list --porcelain | rg 'mgw-071-attempt-1-1779831690|mgw-085-attempt-1-1779837810' || true
jq -r 'select(.type=="merged_worktree_cleanup") | [.timestamp, (.dirty_worktree_groups.unsupported_status.count // 0), (.skipped_reason_counts["dirty_worktree:unsupported_status"] // 0)] | @tsv' /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_supervisor_events.jsonl | tail -n 5
```

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
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status",
  "fingerprint": "731f0bb0db091c0d6d7bbf9d8746d1f86e43646e",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "unsupported_status",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/mgw-071-attempt-1-1779831690",
    "implementation/mgw-085-attempt-1-1779837810"
  ],
  "sample_count": 2,
  "sample_status_paths": [
    "external/meta-wearables-dat-android",
    "swissknife"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-071-attempt-1-1779831690",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-085-attempt-1-1779837810"
  ],
  "success_signals": [
    "candidate_count_decreases",
    "dirty_worktree_group_count_decreases",
    "main_checkout_dirty_becomes_false",
    "cleanup_or_reconciliation_pass_processes_candidates"
  ]
}
```
