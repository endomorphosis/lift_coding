# VAI-200 Reconciliation Guardrail

Date: 2026-06-24
Fingerprint: a1539fb6313c7baa261d85f4ca8bd6dc3b8c5fdd
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 23
Priority: P1
Track: ops

## Main Checkout Status

- `?? hallucinate-start-post-sysctl.log`

## Main Checkout Evidence

- Path categories: `untracked=1`
- Status paths:
  - `hallucinate-start-post-sysctl.log`
- Untracked paths:
  - `hallucinate-start-post-sysctl.log`

## Sample Branches Or Worktrees

- `implementation/vai-387-attempt-1-1782270557` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-387-attempt-1-1782270557`
- `implementation/vai-388-attempt-1-1782270568` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-388-attempt-1-1782270568`
- `implementation/vai-390-attempt-1-1782271001` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-390-attempt-1-1782271001`
- `implementation/vai-391-attempt-1-1782271083` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-391-attempt-1-1782271083`
- `implementation/vai-392-attempt-1-1782271540` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-392-attempt-1-1782271540`
- `implementation/vai-396-attempt-1-1782272127` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-396-attempt-1-1782272127`
- `implementation/vai-399-attempt-1-1782272601` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-399-attempt-1-1782272601`
- `implementation/vai-400-attempt-1-1782272626` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-400-attempt-1-1782272626`
- `implementation/vai-401-attempt-1-1782273617` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-401-attempt-1-1782273617`
- `implementation/vai-403-attempt-1-1782273965` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-403-attempt-1-1782273965`
- `implementation/vai-406-attempt-1-1782274280` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-406-attempt-1-1782274280`
- `implementation/vai-408-attempt-1-1782274810` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-408-attempt-1-1782274810`
- `implementation/vai-409-attempt-1-1782274706` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-409-attempt-1-1782274706`
- `implementation/vai-411-attempt-1-1782275130` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-411-attempt-1-1782275130`
- `implementation/vai-412-attempt-1-1782275200` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-412-attempt-1-1782275200`
- `implementation/vai-414-attempt-1-1782275674` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-414-attempt-1-1782275674`
- `implementation/vai-415-attempt-1-1782275738` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-415-attempt-1-1782275738`
- `rescue/worktree/implementation-vai-418-attempt-1-1782276227-ec35d5b8594a` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-418-attempt-1-1782276227`
- `implementation/vai-421-attempt-1-1782276524` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-421-attempt-1-1782276524`
- `implementation/vai-426-attempt-1-1782277180` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-426-attempt-1-1782277180`

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

Work surface: `23` candidates, `20` sampled records.

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
  "candidate_count": 23,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "a1539fb6313c7baa261d85f4ca8bd6dc3b8c5fdd",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "path_categories": {
      "untracked": 1
    },
    "status_paths": [
      "hallucinate-start-post-sysctl.log"
    ],
    "status_short": [
      "?? hallucinate-start-post-sysctl.log"
    ],
    "untracked_paths": [
      "hallucinate-start-post-sysctl.log"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
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
    "hallucinate-start-post-sysctl.log"
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
