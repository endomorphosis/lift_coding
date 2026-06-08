# MGW-242 Reconciliation Guardrail

Date: 2026-06-08
Fingerprint: 081b1763ca241d20fc52b6d24168f345d13b2446
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 15
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/mgw-001-attempt-2-1779440464` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-001-attempt-2-1779440464`
  - Conflict paths:
    - `implementation_plan/docs/00-overview.md`
    - `implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `scripts/meta_glasses_display_llm_router.py`
    - `scripts/meta_glasses_display_todo_daemon.py`
    - `scripts/meta_glasses_display_todo_supervisor.py`
    - `tests/test_meta_glasses_display_todo_queue.py`
- `implementation/mgw-060-attempt-1-1779826861` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-060-attempt-1-1779826861`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-060-resolution.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `tests/test_hallucinate_multimodal_control_todo_queue.py`
- `implementation/mgw-112-attempt-1-1779876522` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-112-attempt-1-1779876522`
  - Conflict paths:
    - `work/PR-081-privacy-mode-per-profile.md`
- `implementation/mgw-123-attempt-1-1779885204` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-123-attempt-1-1779885204`
  - Conflict paths:
    - `hallucinate_app`
- `implementation/mgw-139-attempt-1-1779955983` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-139-attempt-1-1779955983`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-139-resolution.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `implementation/mgw-142-attempt-1-1779957075` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-142-attempt-1-1779957075`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-142-resolution.md`
    - `data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md`
- `implementation/mgw-145-attempt-1-1779959122` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-145-attempt-1-1779959122`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `implementation/mgw-154-attempt-1-1779966217` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-154-attempt-1-1779966217`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-resolution.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `implementation/mgw-157-attempt-2-1779969617` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-157-attempt-2-1779969617`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-resolution.md`
    - `data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md`
- `implementation/mgw-162-attempt-1-1779973744` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-162-attempt-1-1779973744`
  - Conflict paths:
    - `data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `implementation/mgw-169-attempt-3-1780157080` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-169-attempt-3-1780157080`
  - Conflict paths:
    - `data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md`
- `implementation/mgw-202-attempt-2-1780231669` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-202-attempt-2-1780231669`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-202-resolution.md`
    - `data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md`
- `implementation/mgw-214-attempt-1-1780245390` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-214-attempt-1-1780245390`
  - Conflict paths:
    - `data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-214-resolution.md`
    - `data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md`
    - `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- `implementation/mgw-224-attempt-1-1780714601` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-224-attempt-1-1780714601`
  - Conflict paths:
    - `data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md`
    - `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- `implementation/mgw-271-attempt-4-1780902619` at `/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-271-attempt-4-1780902619`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

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

Work surface: `15` candidates, `15` sampled records.

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
  "candidate_count": 15,
  "conflict_path_counts": {
    "data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-060-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-139-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-142-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-202-resolution.md": 1,
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-214-resolution.md": 1,
    "data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md": 1,
    "data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md": 1,
    "data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md": 1,
    "data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md": 1,
    "data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md": 2,
    "data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md": 1,
    "hallucinate_app": 1,
    "implementation_plan/docs/00-overview.md": 1,
    "implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md": 1,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md": 1,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 7,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 1,
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md": 2,
    "scripts/meta_glasses_display_llm_router.py": 1,
    "scripts/meta_glasses_display_todo_daemon.py": 1,
    "scripts/meta_glasses_display_todo_supervisor.py": 1,
    "tests/test_hallucinate_multimodal_control_todo_queue.py": 1,
    "tests/test_meta_glasses_display_todo_queue.py": 1,
    "work/PR-081-privacy-mode-per-profile.md": 1
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "081b1763ca241d20fc52b6d24168f345d13b2446",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/mgw-001-attempt-2-1779440464",
    "implementation/mgw-060-attempt-1-1779826861",
    "implementation/mgw-112-attempt-1-1779876522",
    "implementation/mgw-123-attempt-1-1779885204",
    "implementation/mgw-139-attempt-1-1779955983",
    "implementation/mgw-142-attempt-1-1779957075",
    "implementation/mgw-145-attempt-1-1779959122",
    "implementation/mgw-154-attempt-1-1779966217",
    "implementation/mgw-157-attempt-2-1779969617",
    "implementation/mgw-162-attempt-1-1779973744",
    "implementation/mgw-169-attempt-3-1780157080",
    "implementation/mgw-202-attempt-2-1780231669",
    "implementation/mgw-214-attempt-1-1780245390",
    "implementation/mgw-224-attempt-1-1780714601",
    "implementation/mgw-271-attempt-4-1780902619"
  ],
  "sample_count": 15,
  "sample_status_paths": [
    "implementation_plan/docs/00-overview.md",
    "implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "scripts/meta_glasses_display_llm_router.py",
    "scripts/meta_glasses_display_todo_daemon.py",
    "scripts/meta_glasses_display_todo_supervisor.py",
    "tests/test_meta_glasses_display_todo_queue.py",
    "data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-060-resolution.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "tests/test_hallucinate_multimodal_control_todo_queue.py",
    "work/PR-081-privacy-mode-per-profile.md",
    "hallucinate_app",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-139-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-142-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-202-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-214-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md",
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-001-attempt-2-1779440464",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-060-attempt-1-1779826861",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-112-attempt-1-1779876522",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-123-attempt-1-1779885204",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-139-attempt-1-1779955983",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-142-attempt-1-1779957075",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-145-attempt-1-1779959122",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-154-attempt-1-1779966217",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-157-attempt-2-1779969617",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-162-attempt-1-1779973744",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-169-attempt-3-1780157080",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-202-attempt-2-1780231669",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-214-attempt-1-1780245390",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-224-attempt-1-1780714601",
    "/home/barberb/lift_coding/data/meta_glasses_display_widgets/worktrees/mgw-271-attempt-4-1780902619"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md",
    "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-060-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-139-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-142-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-202-resolution.md",
    "data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-214-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md",
    "data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md",
    "hallucinate_app",
    "implementation_plan/docs/00-overview.md",
    "implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
  ]
}
```
