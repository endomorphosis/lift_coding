# VAI-203 Reconciliation Guardrail

Date: 2026-06-24
Fingerprint: d08b914cebb5cc024ee666b84764644945789001
Kind: preflight_merge_conflict
Reason: preflight_merge_conflict
Candidate count: 32
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `implementation/vai-387-attempt-1-1782270557` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-387-attempt-1-1782270557`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `swissknife`
- `implementation/vai-388-attempt-1-1782270568` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-388-attempt-1-1782270568`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `swissknife`
- `implementation/vai-390-attempt-1-1782271001` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-390-attempt-1-1782271001`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/vai-391-attempt-1-1782271083` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-391-attempt-1-1782271083`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/vai-392-attempt-1-1782271540` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-392-attempt-1-1782271540`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/vai-396-attempt-1-1782272127` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-396-attempt-1-1782272127`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/vai-399-attempt-1-1782272601` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-399-attempt-1-1782272601`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/vai-400-attempt-1-1782272626` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-400-attempt-1-1782272626`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/vai-401-attempt-1-1782273617` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-401-attempt-1-1782273617`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `swissknife`
- `implementation/vai-403-attempt-1-1782273965` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-403-attempt-1-1782273965`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-406-attempt-1-1782274280` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-406-attempt-1-1782274280`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-408-attempt-1-1782274810` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-408-attempt-1-1782274810`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-409-attempt-1-1782274706` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-409-attempt-1-1782274706`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-411-attempt-1-1782275130` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-411-attempt-1-1782275130`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `swissknife`
- `implementation/vai-412-attempt-1-1782275200` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-412-attempt-1-1782275200`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-414-attempt-1-1782275674` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-414-attempt-1-1782275674`
  - Conflict paths:
    - `swissknife`
- `implementation/vai-415-attempt-1-1782275738` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-415-attempt-1-1782275738`
  - Conflict paths:
    - `swissknife`
- `rescue/worktree/implementation-vai-418-attempt-1-1782276227-ec35d5b8594a` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-418-attempt-1-1782276227`
  - Conflict paths:
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
    - `swissknife`
- `implementation/vai-421-attempt-1-1782276524` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-421-attempt-1-1782276524`
  - Conflict paths:
    - `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
    - `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
- `implementation/vai-426-attempt-1-1782277180` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-426-attempt-1-1782277180`
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

Work surface: `32` candidates, `20` sampled records.

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
  "candidate_count": 32,
  "conflict_path_counts": {
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md": 18,
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md": 12,
    "swissknife": 26
  },
  "dedupe_key": "reconciliation_guardrail:preflight_merge_conflict",
  "fingerprint": "d08b914cebb5cc024ee666b84764644945789001",
  "kind": "preflight_merge_conflict",
  "main_dirty_evidence": {},
  "reason": "preflight_merge_conflict",
  "safety_constraints": [
    "Do not run conflict-producing merges directly in main without a preflight or isolated resolver plan.",
    "Preserve submodule gitlink intent explicitly; never pick a gitlink side without recording why.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-387-attempt-1-1782270557",
    "implementation/vai-388-attempt-1-1782270568",
    "implementation/vai-390-attempt-1-1782271001",
    "implementation/vai-391-attempt-1-1782271083",
    "implementation/vai-392-attempt-1-1782271540",
    "implementation/vai-396-attempt-1-1782272127",
    "implementation/vai-399-attempt-1-1782272601",
    "implementation/vai-400-attempt-1-1782272626",
    "implementation/vai-401-attempt-1-1782273617",
    "implementation/vai-403-attempt-1-1782273965",
    "implementation/vai-406-attempt-1-1782274280",
    "implementation/vai-408-attempt-1-1782274810",
    "implementation/vai-409-attempt-1-1782274706",
    "implementation/vai-411-attempt-1-1782275130",
    "implementation/vai-412-attempt-1-1782275200",
    "implementation/vai-414-attempt-1-1782275674",
    "implementation/vai-415-attempt-1-1782275738",
    "rescue/worktree/implementation-vai-418-attempt-1-1782276227-ec35d5b8594a",
    "implementation/vai-421-attempt-1-1782276524",
    "implementation/vai-426-attempt-1-1782277180"
  ],
  "sample_count": 20,
  "sample_status_paths": [
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "swissknife",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-387-attempt-1-1782270557",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-388-attempt-1-1782270568",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-390-attempt-1-1782271001",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-391-attempt-1-1782271083",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-392-attempt-1-1782271540",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-396-attempt-1-1782272127",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-399-attempt-1-1782272601",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-400-attempt-1-1782272626",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-401-attempt-1-1782273617",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-403-attempt-1-1782273965",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-406-attempt-1-1782274280",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-408-attempt-1-1782274810",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-409-attempt-1-1782274706",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-411-attempt-1-1782275130",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-412-attempt-1-1782275200",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-414-attempt-1-1782275674",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-415-attempt-1-1782275738",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-418-attempt-1-1782276227",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-421-attempt-1-1782276524",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-426-attempt-1-1782277180"
  ],
  "success_signals": [
    "preflight_blocked_count_decreases",
    "conflict_path_count_decreases",
    "reconciled_count_increases",
    "main_checkout_dirty_becomes_false"
  ],
  "top_conflict_paths": [
    "swissknife",
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
    "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md"
  ]
}
```
