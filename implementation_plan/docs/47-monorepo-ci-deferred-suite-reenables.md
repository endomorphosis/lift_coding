# Monorepo CI deferred suite re-enables (CIG)

**Status:** Active  
**Board:** `implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md`  
**Prefix:** `## CIG-`  
**Date:** 2026-08-06  

## Purpose

After waves that restored main green and re-enabled Profile-H, guardrails, meta
glasses board tests, accelerate interop, e2e connectivity, and desktop app
integrations, a residual set of `test-ci` suites remains ignored in the
root `Makefile`. This program files those suites as
`ipfs_accelerate_py.agent_supervisor`-parseable tasks so agents can claim and
implement them in parallel worktrees.

## Already re-enabled (do not refile)

| Suite | Landed in |
| --- | --- |
| Virtual AI OS harnesses (non-todo-queue) | #464 |
| Profile-H inventory/spec + package | #470 / #472 |
| Reconciliation guardrail refresh | #472 |
| Meta glasses display todo queue | #472 |
| SwissKnife ↔ accelerate interop | #473 |
| e2e connectivity | #473 |
| Desktop app integrations | #473 |

## Deferred inventory (this board)

### Interop / descriptor drift

| Task | Suite / surface | Primary drift |
| --- | --- | --- |
| CIG-010 | `tests/integration/test_swissknife_mcp_plus_plus_interop.py` | Receipt schema multi-daemon enums; fixture `task_id` |
| CIG-011 | `tests/integration/test_swissknife_mobile_interop.py` | MGW renumber; validation shape |
| CIG-012 | `tests/integration/test_orb_dynamic_renderer.py` | UIR-035 renderer API/UI string rewrite |
| CIG-013 | `tests/integration/test_swissknife_external_ipfs_datasets_interop.py` | Missing nested `.tools/ipfs_kit_py` schema path |
| CIG-014 | `tests/integration/test_hallucinate_app_mobile_interop.py` | Missing nested accelerate schema under hallucinate_app |
| CIG-015 | `tests/integration/test_glasses_control_plane.py` | Missing `meta-glasses-mobile-orb-bridge.ts` (or relocate assert) |
| CIG-016 | `tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py` | Nested DAT + descriptor alignment |
| CIG-017 | `tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py` | Nested DAT + descriptor alignment |
| CIG-018–020 | meta-wearables × accelerate/datasets/kit | Nested DAT android external interops |

### Large board/fixture suites

| Task | Suite |
| --- | --- |
| CIG-030 | `tests/test_virtual_ai_os_todo_queue.py` |
| CIG-031 | `tests/test_hallucinate_multimodal_control_todo_queue.py` |

## Parallelism model

- **Wave A (CIG-010…020):** independent `predicted_files` where possible; claim
  in parallel on distinct lanes (`cig-mcp`, `cig-mobile`, `cig-orb`, …).
- **Wave B (CIG-030/031):** large fixture boards; serial relative to each other
  optional but prefer separate lanes; do not fan out internal board tasks here.
- **Wave C (CIG-040):** closeout only after Wave A+B land and `Makefile`
  `test-ci` ignore list no longer lists those suites (except intentional
  long-term exclusions documented on the board).

Conflict policy: no two claimable tasks may share a non-empty predicted file
path. Shared `Makefile` edits are owned only by closeout (CIG-040) or by
explicit single-owner tasks that list `Makefile` alone for their ignore-line
removal.

## Supervisor entry

```bash
# Parse / dry-run selection (requires external/ipfs_accelerate checkout)
PYTHONPATH=external/ipfs_accelerate python3 scripts/monorepo_ci_reenables_todo_supervisor.py --once

# Full implementation supervisor (leased worktrees when configured)
PYTHONPATH=src:external/ipfs_accelerate python3 -m \
  ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
  --todo-path implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md \
  --task-prefix '## CIG-'
```

Parser smoke tests: `tests/test_monorepo_ci_reenables_todo_queue.py`.

## Success criteria

1. Each Wave A/B task re-enables its suite (or documents a permanent ignore with
   rationale in the task acceptance).
2. CI `check` stays green on main after each merge.
3. CIG-040 records the final ignore list and remaining intentional exclusions.
