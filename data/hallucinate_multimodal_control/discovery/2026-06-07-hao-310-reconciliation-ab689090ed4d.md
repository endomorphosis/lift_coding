# HAO-310 Reconciliation Guardrail

Date: 2026-06-09
Fingerprint: 4be543b68e7dd3d4e830d4e83089e5046602d128
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

- `implementation/hao-306-attempt-8-1780836137` at `/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-306-attempt-8-1780836137` status: ` m hallucinate_app`
  - Name status:
    - `M	hallucinate_app`
  - Diff stat:
    - `hallucinate_app | 0`
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
  "fingerprint": "4be543b68e7dd3d4e830d4e83089e5046602d128",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "unsupported_status",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/hao-306-attempt-8-1780836137"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "hallucinate_app"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-306-attempt-8-1780836137"
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

Recorded during HAO-310 reconciliation on 2026-06-07.

- Confirmed all `14` sampled implementation branches were already ancestors of
  `main` before cleanup.
- Preserved dirty source and untracked content under
  `data/hallucinate_multimodal_control/discovery/hao-310-preserved-diffs/`
  before resetting the stale worktrees. The preservation set contains `37`
  files: per-worktree outer patches, `hallucinate_app` or `swissknife`
  submodule patches, the `external/ipfs_kit` patch for HAO-308, and copied
  untracked text artifacts.
- Reset and cleaned the sampled outer worktrees and the dirty configured
  submodules (`hallucinate_app`, `swissknife`, and `external/ipfs_kit`) after
  preservation.
- Confirmed all `14` sampled worktrees reported clean status before rerunning
  the supervisor cleanup pass.
- Reran the supervisor cleanup/reconciliation pass from the main checkout:

```sh
python scripts/hallucinate_multimodal_control_todo_supervisor.py --once --reconciliation-only --no-worktree-scan-cache --worktree-reconciliation-max-merges 0 --log-level INFO
```

Latest `merged_worktree_cleanup` event from
`/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_supervisor_events.jsonl`:

- Timestamp: `2026-06-07T09:29:41.139137+00:00`
- `removed_count`: `14`
- Removed branches: `implementation/hao-004-attempt-1-1779564069`,
  `implementation/hao-006-attempt-1-1779570991`,
  `implementation/hao-064-attempt-1-1779742161`,
  `implementation/hao-171-attempt-1-1779877530`,
  `implementation/hao-187-attempt-1-1779947932`,
  `implementation/hao-202-attempt-1-1779958389`,
  `implementation/hao-203-attempt-1-1779959920`,
  `implementation/hao-207-attempt-1-1779964806`,
  `implementation/hao-210-attempt-1-1779969102`,
  `implementation/hao-213-attempt-1-1779968142`,
  `implementation/hao-214-attempt-1-1779973133`,
  `implementation/hao-216-attempt-1-1779974669`,
  `implementation/hao-289-attempt-1-1780714919`, and
  `implementation/hao-308-attempt-1-1780822649`.
- `skipped_reason_counts`: `not_merged=27`, `dirty_worktree=48`,
  `dirty_worktree:content_not_in_target=48`, `active_state_worktree=1`.
- `dirty_worktree_groups`: `content_not_in_target=48`.
- `dirty_worktree:unsupported_status` after cleanup: absent / `0`.
- `scan_cache_hit_count`: `0`.

Verification commands:

```sh
git -C /home/barberb/lift_coding worktree list --porcelain | rg 'hao-004-attempt-1-1779564069|hao-006-attempt-1-1779570991|hao-064-attempt-1-1779742161|hao-171-attempt-1-1779877530|hao-187-attempt-1-1779947932|hao-202-attempt-1-1779958389|hao-203-attempt-1-1779959920|hao-207-attempt-1-1779964806|hao-210-attempt-1-1779969102|hao-213-attempt-1-1779968142|hao-214-attempt-1-1779973133|hao-216-attempt-1-1779974669|hao-289-attempt-1-1780714919|hao-308-attempt-1-1780822649' || true
jq -r 'select(.type=="merged_worktree_cleanup") | [.timestamp, (.removed_count // 0), (.skipped_reason_counts["dirty_worktree:unsupported_status"] // 0), (.dirty_worktree_groups.unsupported_status.count // 0)] | @tsv' /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_supervisor_events.jsonl | tail -n 5
```

Success signal: the HAO-310 `unsupported_status` blocked candidate count
decreased from `14` to `0`, and the supervisor removed all `14` sampled stale
merged worktree registrations.
