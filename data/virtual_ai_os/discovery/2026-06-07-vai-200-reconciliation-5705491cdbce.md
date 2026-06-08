# VAI-200 Reconciliation Guardrail

Date: 2026-06-08
Fingerprint: c012774fafad03ce1750f346c084105a97629c1d
Kind: main_checkout_dirty
Reason: main_checkout_dirty
Candidate count: 47
Priority: P1
Track: ops

## Main Checkout Status

- ` M .handsfree_transport_sessions.json`
- ` M external/ipfs_kit`

## Main Checkout Evidence

- Path categories: `modified=2`
- Status paths:
  - `.handsfree_transport_sessions.json`
  - `external/ipfs_kit`
- Name status:
  - `M	.handsfree_transport_sessions.json`
  - `M	external/ipfs_kit`

## Sample Branches Or Worktrees

- `implementation/vai-042-attempt-1-1779816389` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-042-attempt-1-1779816389`
- `implementation/vai-054-attempt-1-1779827423` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-054-attempt-1-1779827423`
- `implementation/vai-079-attempt-1-1779841991` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-079-attempt-1-1779841991`
- `implementation/vai-095-attempt-1-1779875087` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-095-attempt-1-1779875087`
- `implementation/vai-097-attempt-1-1779873902` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-097-attempt-1-1779873902`
- `implementation/vai-108-attempt-3-1779889162` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-108-attempt-3-1779889162`
- `implementation/vai-116-attempt-1-1779953956` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-116-attempt-1-1779953956`
- `implementation/vai-119-attempt-1-1779957414` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-119-attempt-1-1779957414`
- `implementation/vai-121-attempt-1-1779958261` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-121-attempt-1-1779958261`
- `implementation/vai-124-attempt-1-1779964094` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-124-attempt-1-1779964094`
- `implementation/vai-126-attempt-1-1779960486` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-126-attempt-1-1779960486`
- `implementation/vai-128-attempt-1-1779961507` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-128-attempt-1-1779961507`
- `implementation/vai-135-attempt-1-1779974033` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-135-attempt-1-1779974033`
- `implementation/vai-136-attempt-1-1779974850` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-136-attempt-1-1779974850`
- `implementation/vai-137-attempt-1-1779970867` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-137-attempt-1-1779970867`
- `implementation/vai-142-attempt-1-1779976578` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-142-attempt-1-1779976578`
- `implementation/vai-142-attempt-1-1779977419` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-142-attempt-1-1779977419`
- `implementation/vai-143-attempt-1-1779976871` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-143-attempt-1-1779976871`
- `implementation/vai-147-attempt-1-1780160070` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-147-attempt-1-1780160070`
- `implementation/vai-147-attempt-1-1780162217` at `/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-147-attempt-1-1780162217`

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

Work surface: `47` candidates, `20` sampled records.

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
  "candidate_count": 47,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:main_checkout_dirty",
  "fingerprint": "c012774fafad03ce1750f346c084105a97629c1d",
  "kind": "main_checkout_dirty",
  "main_dirty_evidence": {
    "filtered_generated_status_paths": [
      "data/virtual_ai_os/discovery/2026-06-08-vai-238-codebase-scan-372c9f0bf55f.md"
    ],
    "name_status": "M\t.handsfree_transport_sessions.json\nM\texternal/ipfs_kit",
    "path_categories": {
      "modified": 2
    },
    "status_paths": [
      ".handsfree_transport_sessions.json",
      "external/ipfs_kit"
    ],
    "status_short": [
      " M .handsfree_transport_sessions.json",
      " M external/ipfs_kit"
    ]
  },
  "reason": "main_checkout_dirty",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "implementation/vai-042-attempt-1-1779816389",
    "implementation/vai-054-attempt-1-1779827423",
    "implementation/vai-079-attempt-1-1779841991",
    "implementation/vai-095-attempt-1-1779875087",
    "implementation/vai-097-attempt-1-1779873902",
    "implementation/vai-108-attempt-3-1779889162",
    "implementation/vai-116-attempt-1-1779953956",
    "implementation/vai-119-attempt-1-1779957414",
    "implementation/vai-121-attempt-1-1779958261",
    "implementation/vai-124-attempt-1-1779964094",
    "implementation/vai-126-attempt-1-1779960486",
    "implementation/vai-128-attempt-1-1779961507",
    "implementation/vai-135-attempt-1-1779974033",
    "implementation/vai-136-attempt-1-1779974850",
    "implementation/vai-137-attempt-1-1779970867",
    "implementation/vai-142-attempt-1-1779976578",
    "implementation/vai-142-attempt-1-1779977419",
    "implementation/vai-143-attempt-1-1779976871",
    "implementation/vai-147-attempt-1-1780160070",
    "implementation/vai-147-attempt-1-1780162217"
  ],
  "sample_count": 20,
  "sample_status_paths": [
    ".handsfree_transport_sessions.json",
    "external/ipfs_kit"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-042-attempt-1-1779816389",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-054-attempt-1-1779827423",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-079-attempt-1-1779841991",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-095-attempt-1-1779875087",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-097-attempt-1-1779873902",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-108-attempt-3-1779889162",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-116-attempt-1-1779953956",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-119-attempt-1-1779957414",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-121-attempt-1-1779958261",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-124-attempt-1-1779964094",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-126-attempt-1-1779960486",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-128-attempt-1-1779961507",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-135-attempt-1-1779974033",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-136-attempt-1-1779974850",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-137-attempt-1-1779970867",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-142-attempt-1-1779976578",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-142-attempt-1-1779977419",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-143-attempt-1-1779976871",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-147-attempt-1-1780160070",
    "/home/barberb/lift_coding/data/virtual_ai_os/worktrees/vai-147-attempt-1-1780162217"
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
