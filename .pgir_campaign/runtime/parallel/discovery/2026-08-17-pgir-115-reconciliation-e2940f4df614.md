# PGIR-115 Reconciliation Guardrail

Date: 2026-08-17
Fingerprint: e2940f4df61491aed9a68997a1292c79799d36ea
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 1
Priority: P1
Track: ops

## Main Checkout Status

- ` M ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py`

## Main Checkout Evidence

- Path categories: `modified=1`
- Status paths:
  - `ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py`
- Name status:
  - `M	ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py`
- Diff stat:
  - `.../validation/proposal_validation.py              | 41 ++++++++++++++++++++++`
  - ` 1 file changed, 41 insertions(+)`

## Sample Branches Or Worktrees

- `rescue/worktree/implementation-pgir-060-d2c6b71e0110-attempt-1-1786946656-2b2ccc291a04` at `/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-f5dee7c34fb0-48dd2afadccc`

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

- `classify_main_checkout_changes`: inspect git status, diff stats, submodule status, and generated artifacts before merges
- `preserve_or_split_main_checkout_work`: commit intentional changes or convert unresolved changes into follow-up tasks; never discard unknown work
- `rerun_worktree_reconciliation`: rerun reconcile_backlogged_worktrees once the main checkout is clean enough to mutate

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
      "action": "classify_main_checkout_changes",
      "automation": "inspect git status, diff stats, submodule status, and generated artifacts before merges",
      "scope": "repo_root"
    },
    {
      "action": "preserve_or_split_main_checkout_work",
      "automation": "commit intentional changes or convert unresolved changes into follow-up tasks; never discard unknown work",
      "scope": "repo_root"
    },
    {
      "action": "rerun_worktree_reconciliation",
      "automation": "rerun reconcile_backlogged_worktrees once the main checkout is clean enough to mutate",
      "scope": "backlogged_worktrees"
    }
  ],
  "candidate_count": 1,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "e2940f4df61491aed9a68997a1292c79799d36ea",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "diff_stat": ".../validation/proposal_validation.py              | 41 ++++++++++++++++++++++\n 1 file changed, 41 insertions(+)",
    "name_status": "M\tipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py",
    "path_categories": {
      "modified": 1
    },
    "status_paths": [
      "ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py"
    ],
    "status_short": [
      " M ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/implementation-pgir-060-d2c6b71e0110-attempt-1-1786946656-2b2ccc291a04"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "ipfs_accelerate_py/agent_supervisor/validation/proposal_validation.py"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-f5dee7c34fb0-48dd2afadccc"
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
