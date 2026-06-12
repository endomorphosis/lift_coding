# VAI-200 Reconciliation Guardrail

Date: 2026-06-12
Fingerprint: 001610d17dace5d566aa04d874faa4fea47b6f8d
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 25
Priority: P1
Track: ops

## Main Checkout Status

- `M  data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
- `M  data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
- `M  hallucinate_app`

## Main Checkout Evidence

- Path categories: `modified=3`
- Status paths:
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
  - `data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `hallucinate_app`
- Staged name status:
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md`
  - `M	data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md`
  - `M	hallucinate_app`

## Sample Branches Or Worktrees

- `implementation/vai-001-attempt-1-1781231623` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-001-attempt-1-1781231623`
- `implementation/vai-002-attempt-1-1781232308` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-002-attempt-1-1781232308`
- `implementation/vai-003-attempt-1-1781233228` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-003-attempt-1-1781233228`
- `implementation/vai-004-attempt-1-1781233842` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-004-attempt-1-1781233842`
- `implementation/vai-005-attempt-1-1781234570` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-005-attempt-1-1781234570`
- `implementation/vai-006-attempt-1-1781234828` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-006-attempt-1-1781234828`
- `rescue/worktree/implementation-vai-007-attempt-1-1781235196-8938c564e46e` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-007-attempt-1-1781235196`
- `implementation/vai-045-attempt-1-1780994816` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-045-attempt-1-1780994816`
- `implementation/vai-046-attempt-1-1780995526` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-046-attempt-1-1780995526`
- `implementation/vai-107-attempt-1-1780996157` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-107-attempt-1-1780996157`
- `implementation/vai-126-attempt-1-1780996866` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-126-attempt-1-1780996866`
- `implementation/vai-127-attempt-1-1780999997` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-127-attempt-1-1780999997`
- `implementation/vai-214-attempt-1-1780995799` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-214-attempt-1-1780995799`
- `implementation/vai-215-attempt-1-1780997204` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-215-attempt-1-1780997204`
- `implementation/vai-216-attempt-1-1780997982` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-216-attempt-1-1780997982`
- `implementation/vai-218-attempt-1-1780999166` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-218-attempt-1-1780999166`
- `implementation/vai-317-attempt-1-1781226464` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-317-attempt-1-1781226464`
- `implementation/vai-317-attempt-1-1781236192` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-317-attempt-1-1781236192`
- `implementation/vai-318-attempt-1-1781226886` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-318-attempt-1-1781226886`
- `rescue/worktree/implementation-vai-319-attempt-1-1781227562-62fae97ef71a` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-319-attempt-1-1781227562`

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

Work surface: `25` candidates, `20` sampled records.

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
  "candidate_count": 25,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "001610d17dace5d566aa04d874faa4fea47b6f8d",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "filtered_generated_status_paths": [
      "data/virtual_ai_os/discovery/2026-06-07-vai-200-reconciliation-5705491cdbce.md",
      "data/virtual_ai_os/discovery/2026-06-12-vai-318-vai-045-merge-retry-budget.md",
      "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
    ],
    "path_categories": {
      "modified": 3
    },
    "staged_name_status": "M\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md\nM\tdata/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md\nM\thallucinate_app",
    "status_paths": [
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
      "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      "hallucinate_app"
    ],
    "status_short": [
      "M  data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
      "M  data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
      "M  hallucinate_app"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-001-attempt-1-1781231623",
    "implementation/vai-002-attempt-1-1781232308",
    "implementation/vai-003-attempt-1-1781233228",
    "implementation/vai-004-attempt-1-1781233842",
    "implementation/vai-005-attempt-1-1781234570",
    "implementation/vai-006-attempt-1-1781234828",
    "rescue/worktree/implementation-vai-007-attempt-1-1781235196-8938c564e46e",
    "implementation/vai-045-attempt-1-1780994816",
    "implementation/vai-046-attempt-1-1780995526",
    "implementation/vai-107-attempt-1-1780996157",
    "implementation/vai-126-attempt-1-1780996866",
    "implementation/vai-127-attempt-1-1780999997",
    "implementation/vai-214-attempt-1-1780995799",
    "implementation/vai-215-attempt-1-1780997204",
    "implementation/vai-216-attempt-1-1780997982",
    "implementation/vai-218-attempt-1-1780999166",
    "implementation/vai-317-attempt-1-1781226464",
    "implementation/vai-317-attempt-1-1781236192",
    "implementation/vai-318-attempt-1-1781226886",
    "rescue/worktree/implementation-vai-319-attempt-1-1781227562-62fae97ef71a"
  ],
  "sample_count": 20,
  "sample_status_paths": [
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-309-reconciliation-c05f71151a70.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-07-hao-311-reconciliation-534cc45af3d6.md",
    "hallucinate_app"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-001-attempt-1-1781231623",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-002-attempt-1-1781232308",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-003-attempt-1-1781233228",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-004-attempt-1-1781233842",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-005-attempt-1-1781234570",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-006-attempt-1-1781234828",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-007-attempt-1-1781235196",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-045-attempt-1-1780994816",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-046-attempt-1-1780995526",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-107-attempt-1-1780996157",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-126-attempt-1-1780996866",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-127-attempt-1-1780999997",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-214-attempt-1-1780995799",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-215-attempt-1-1780997204",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-216-attempt-1-1780997982",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-218-attempt-1-1780999166",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-317-attempt-1-1781226464",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-317-attempt-1-1781236192",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-318-attempt-1-1781226886",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-319-attempt-1-1781227562"
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
