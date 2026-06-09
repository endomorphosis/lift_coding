# VAI-200 Reconciliation Guardrail

Date: 2026-06-09
Fingerprint: 5e7b38a671306cd66be492578467b7ace5fd5a27
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 4
Priority: P1
Track: ops

## Main Checkout Status

- ` M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
- ` M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
- ` M data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md`
- ` m hallucinate_app`
- ` M implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

## Main Checkout Evidence

- Path categories: `modified=4, other_dirty=1`
- Status paths:
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md`
  - `hallucinate_app`
  - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- Name status:
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `M	data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md`
  - `M	hallucinate_app`
  - `M	implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

## Sample Branches Or Worktrees

- `implementation/vai-154-attempt-1-1780988946` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-154-attempt-1-1780988946`
- `implementation/vai-155-attempt-1-1780989245` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-155-attempt-1-1780989245`
- `implementation/vai-156-attempt-1-1780989516` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-156-attempt-1-1780989516`
- `implementation/vai-202-attempt-1-1780989786` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-202-attempt-1-1780989786`

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

Work surface: `4` candidates, `4` sampled records.

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
  "candidate_count": 4,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "5e7b38a671306cd66be492578467b7ace5fd5a27",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "filtered_generated_status_paths": [
      "data/virtual_ai_os/discovery/2026-06-07-vai-200-reconciliation-5705491cdbce.md"
    ],
    "name_status": "M\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md\nM\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md\nM\tdata/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md\nM\thallucinate_app\nM\timplementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "path_categories": {
      "modified": 4,
      "other_dirty": 1
    },
    "status_paths": [
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      "data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md",
      "hallucinate_app",
      "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md"
    ],
    "status_short": [
      " M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
      " M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      " M data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md",
      " m hallucinate_app",
      " M implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-154-attempt-1-1780988946",
    "implementation/vai-155-attempt-1-1780989245",
    "implementation/vai-156-attempt-1-1780989516",
    "implementation/vai-202-attempt-1-1780989786"
  ],
  "sample_count": 4,
  "sample_status_paths": [
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md",
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-154-attempt-1-1780988946",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-155-attempt-1-1780989245",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-156-attempt-1-1780989516",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-202-attempt-1-1780989786"
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
