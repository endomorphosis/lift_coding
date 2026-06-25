# VAI-200 Reconciliation Guardrail

Date: 2026-06-25
Fingerprint: 3782f568fd1c47fcdccbba0aa61fa445dfb72e3f
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 1
Priority: P1
Track: ops

## Main Checkout Status

- ` m hallucinate_app`
- ` M scripts/run_vai_mgw_hao_supervisors.py`
- ` M tests/test_virtual_ai_os_todo_queue.py`

## Main Checkout Evidence

- Path categories: `modified=2, other_dirty=1`
- Status paths:
  - `hallucinate_app`
  - `scripts/run_vai_mgw_hao_supervisors.py`
  - `tests/test_virtual_ai_os_todo_queue.py`
- Name status:
  - `M	hallucinate_app`
  - `M	scripts/run_vai_mgw_hao_supervisors.py`
  - `M	tests/test_virtual_ai_os_todo_queue.py`

## Sample Branches Or Worktrees

- `implementation/vai-503-attempt-1-1782421864` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-1-1782421864`

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
  "fingerprint": "3782f568fd1c47fcdccbba0aa61fa445dfb72e3f",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "filtered_generated_status_paths": [
      "data/virtual_ai_os/discovery/2026-06-07-vai-200-reconciliation-5705491cdbce.md",
      "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
    ],
    "name_status": "M\thallucinate_app\nM\tscripts/run_vai_mgw_hao_supervisors.py\nM\ttests/test_virtual_ai_os_todo_queue.py",
    "path_categories": {
      "modified": 2,
      "other_dirty": 1
    },
    "status_paths": [
      "hallucinate_app",
      "scripts/run_vai_mgw_hao_supervisors.py",
      "tests/test_virtual_ai_os_todo_queue.py"
    ],
    "status_short": [
      " m hallucinate_app",
      " M scripts/run_vai_mgw_hao_supervisors.py",
      " M tests/test_virtual_ai_os_todo_queue.py"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-503-attempt-1-1782421864"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    "hallucinate_app",
    "scripts/run_vai_mgw_hao_supervisors.py",
    "tests/test_virtual_ai_os_todo_queue.py"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-1-1782421864"
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

Execution on 2026-06-07 classified the main checkout before mutating any
worktree cleanup candidates:

- `git status --short --branch` in `/home/barberb/lift_coding` reported
  `## main...origin/main` with no dirty paths at main commit `79a86cb8`.
- `git diff --cached --stat` and `git diff --stat` were empty, so none of the
  original guardrail dirty paths remained as uncommitted work.
- No dirty or untracked content from the guardrail set was discarded.

The active supervisor then reran worktree reconciliation after the checkout was
clean enough to inspect merge candidates. Structured events in
`data/virtual_ai_os/state/virtual_ai_os_supervisor_events.jsonl` recorded:

- `2026-06-07T07:09:06.785769+00:00`: `worktree_reconciliation`,
  `attempted=true`, `main_checkout_dirty=false`, `candidate_count=15`,
  `reconciled_count=0`.
- `2026-06-07T07:17:26.799537+00:00`: `worktree_reconciliation`,
  `attempted=true`, `main_checkout_dirty=false`, `candidate_count=15`,
  `reconciled_count=0`.

This reduces the VAI-200 dirty-main blocked work surface from the guardrail's
`18` candidates to a post-pass reconciliation candidate count of `15`, with the
`main_checkout_dirty` condition false. The remaining candidates are no longer
blocked by the dirty main checkout; they are carried forward under the separate
dirty-worktree or preflight-conflict guardrails.

During this execution the live supervisor generated additional VAI-201/objective
refill updates after the clean reconciliation pass. Those generated changes were
preserved in main commit `dd61450c` (`Record VAI reconciliation guardrail
refresh`) rather than discarded, leaving the main checkout clean again for the
VAI-200 worktree merge.
