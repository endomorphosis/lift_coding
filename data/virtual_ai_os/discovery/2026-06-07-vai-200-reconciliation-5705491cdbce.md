# VAI-200 Reconciliation Guardrail

Date: 2026-06-26
Fingerprint: d49b0c059e807f44838f3f4302b32eff0a4bc318
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 7
Priority: P1
Track: ops

## Main Checkout Status

- ` M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md`
- ` M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
- ` M hallucinate_app`
- ` M implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

## Main Checkout Evidence

- Path categories: `modified=4`
- Status paths:
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md`
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `hallucinate_app`
  - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- Name status:
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md`
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `M	hallucinate_app`
  - `M	implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-503-attempt-2-5c0f3198fbef` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-2-1782433690`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--c2c60aa93128` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433044`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-512-attempt-1-2b796b1067f5` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433437`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-512-attempt-1-e2bbcde13ae1` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782434708`
- `rescue/worktree/rescue-worktree-implementation-vai-512-attempt-12-1782435836-65e7afff5198-affd447a864d` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782435836`
- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--973897644384` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-3-1782425881`
- `implementation/vai-514-attempt-1-1782427150` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-514-attempt-1-1782427150`

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
  "candidate_count": 7,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "d49b0c059e807f44838f3f4302b32eff0a4bc318",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "filtered_generated_status_paths": [
      "data/virtual_ai_os/discovery/2026-06-07-vai-202-reconciliation-a2e3e24315da.md",
      "data/virtual_ai_os/discovery/2026-06-07-vai-203-reconciliation-19f9d53ba349.md",
      "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
    ],
    "name_status": "M\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md\nM\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md\nM\thallucinate_app\nM\timplementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "path_categories": {
      "modified": 4
    },
    "status_paths": [
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md",
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      "hallucinate_app",
      "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md"
    ],
    "status_short": [
      " M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md",
      " M data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      " M hallucinate_app",
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
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-503-attempt-2-5c0f3198fbef",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--c2c60aa93128",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-512-attempt-1-2b796b1067f5",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-implementation-vai-512-attempt-1-e2bbcde13ae1",
    "rescue/worktree/rescue-worktree-implementation-vai-512-attempt-12-1782435836-65e7afff5198-affd447a864d",
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--973897644384",
    "implementation/vai-514-attempt-1-1782427150"
  ],
  "sample_count": 7,
  "sample_status_paths": [
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-310-reconciliation-ab689090ed4d.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
    "hallucinate_app",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-503-attempt-2-1782433690",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433044",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782433437",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782434708",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-12-1782435836",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-512-attempt-3-1782425881",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-514-attempt-1-1782427150"
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
