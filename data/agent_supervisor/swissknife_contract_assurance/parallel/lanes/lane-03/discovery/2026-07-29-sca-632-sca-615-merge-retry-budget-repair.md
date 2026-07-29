# SCA-632 Repair Complete: SCA-615 Merge Retry-Budget

Date: 2026-07-29
Source task: SCA-615
Follow-up task: SCA-632
Failure kind: merge (`main_branch_checked_out_elsewhere`)

## Root cause

Merge target `agent/swissknife-sca-parallel` was checked out at the shared
worktree `/home/barberb/211-AI/.worktrees/sca-audit-followups`.
`_prepare_main_merge_workspace` failed closed for any target checkout outside
the managed `.main-merge-worktrees` root, so SCA-615 could not integrate after
validation passed (10 consecutive merge failures).

This was an operational merge-workspace blocker, not a semantic content conflict.
`ipfs-accelerate-agent-merge-resolver --apply` was not required.

## Intended SCA-615 implementation (verified committed)

### Parent repository (`agent/swissknife-sca-parallel`)

| Path | Commit |
|------|--------|
| `data/agent_supervisor/swissknife_contract_assurance/evaluation/production-provider-route.json` | `267fff150` (SCA-615) |
| `external/ipfs_accelerate` gitlink | `511d42fdd` via `a8132ab0d` (SCA-632 pointer after SCA-615) |

SCA-615 branch `implementation/sca-615-18619d67439b-attempt-2-1785357545`
is an ancestor of `agent/swissknife-sca-parallel` after fast-forward merge.

### Submodule `external/ipfs_accelerate` (`main`)

| Path | Notes |
|------|-------|
| `ipfs_accelerate_py/agent_supervisor/todo_daemon/contract_packet_provider_router.py` | SCA-615 production packet/review-chain route |
| `ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py` | SCA-615 production wiring + SCA-632 external checkout reuse |
| `test/api/test_agent_supervisor_production_provider_route.py` | SCA-615 acceptance suite |

- SCA-615 content: `620b923f5`
- SCA-632 merge guardrail: `511d42fdd` (main tip)
- `main` fast-forwarded to `511d42fdd`

## Durable fix (SCA-632)

When the merge target is checked out outside the managed merge-worktree root,
reuse that worktree if it is clean (after optional generated-dirty restore).
Only fail with `main_branch_checked_out_elsewhere` when the external checkout
remains dirty. Sets `reused_external_checkout: true` on success.

## Merge integration performed

1. Fast-forward submodule `main` → `620b923f5` then `511d42fdd`
2. Fast-forward `agent/swissknife-sca-parallel` → SCA-615 `267fff150`
3. Commit `a8132ab0d` on agent branch updating gitlink to SCA-632 fix tip

## Validation

```text
python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_production_provider_route.py -q
→ 15 passed
```

## Supervisor release

SCA-615 may be released from strategy `blocked_tasks` once SCA-632 completion
is admitted. Source implementation is integrated; merge workspace guardrail
prevents the same retry-budget loop on clean external target checkouts.

## Status

**REPAIR COMPLETED**
