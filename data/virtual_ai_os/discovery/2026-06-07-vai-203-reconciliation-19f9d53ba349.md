# VAI-203 Reconciliation Guardrail

Date: 2026-06-07
Fingerprint: 7a186e8fa0342104028f52b8e3f9d43eb2091ea0
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 5
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/vai-042-attempt-1-1779816389` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-042-attempt-1-1779816389`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `src/handsfree/api.py`
    - `src/handsfree/ocr/__init__.py`
- `implementation/vai-054-attempt-1-1779827423` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-054-attempt-1-1779827423`
  - Conflict paths:
    - `tests/test_hallucinate_multimodal_control_todo_queue.py`
- `implementation/vai-079-attempt-1-1779841991` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-079-attempt-1-1779841991`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/vai-095-attempt-1-1779875087` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-095-attempt-1-1779875087`
  - Conflict paths:
    - `data/virtual_ai_os/discovery/2026-05-27-vai-095-codebase-scan-6dfbe572b893.md`
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `work/PR-081-privacy-mode-per-profile.md`
- `implementation/vai-097-attempt-1-1779873902` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-097-attempt-1-1779873902`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md`

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

Work surface: `5` candidates, `5` sampled records.

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
  "candidate_count": 5,
  "conflict_path_counts": {
    "data/virtual_ai_os/discovery/2026-05-27-vai-095-codebase-scan-6dfbe572b893.md": 1,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 3,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 2,
    "src/handsfree/api.py": 1,
    "src/handsfree/ocr/__init__.py": 1,
    "tests/test_hallucinate_multimodal_control_todo_queue.py": 1,
    "work/PR-081-privacy-mode-per-profile.md": 1,
    "work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md": 1
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "7a186e8fa0342104028f52b8e3f9d43eb2091ea0",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-042-attempt-1-1779816389",
    "implementation/vai-054-attempt-1-1779827423",
    "implementation/vai-079-attempt-1-1779841991",
    "implementation/vai-095-attempt-1-1779875087",
    "implementation/vai-097-attempt-1-1779873902"
  ],
  "sample_count": 5,
  "sample_status_paths": [
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "src/handsfree/api.py",
    "src/handsfree/ocr/__init__.py",
    "tests/test_hallucinate_multimodal_control_todo_queue.py",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "data/virtual_ai_os/discovery/2026-05-27-vai-095-codebase-scan-6dfbe572b893.md",
    "work/PR-081-privacy-mode-per-profile.md",
    "work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-042-attempt-1-1779816389",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-054-attempt-1-1779827423",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-079-attempt-1-1779841991",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-095-attempt-1-1779875087",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-097-attempt-1-1779873902"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
    "data/virtual_ai_os/discovery/2026-05-27-vai-095-codebase-scan-6dfbe572b893.md",
    "src/handsfree/api.py",
    "src/handsfree/ocr/__init__.py",
    "tests/test_hallucinate_multimodal_control_todo_queue.py",
    "work/PR-081-privacy-mode-per-profile.md",
    "work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md"
  ]
}
```
