# Dependency Guardrail: VAI-200

Created: 2026-06-07T08:28:44.236564+00:00
Fingerprint: 93d99991168a4d462263b90158f1e2f6946a779f
Source task: VAI-200 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-200
Duplicate source lines: 2231, 2233

## Duplicate Task Titles

- Resolve dirty main checkout blocking 50 worktree merges
- Resolve dirty main checkout blocking 15 worktree merges

## Why This Blocks Progress

The implementation daemon only selects tasks whose dependencies are completed.
When an open task depends on a task id that is not present on the board, or on
itself, or participates in a dependency cycle, the task can remain waiting
indefinitely while the supervisor reports no ready work. Duplicate task ids are
also ambiguous because status maps, dependency resolution, and guardrail
releases all key by task id.

## Suggested Repair

Inspect the source task metadata and either add the missing prerequisite task,
remove the stale dependency, break the dependency cycle, rename duplicate task
ids so each task is unique, or replace stale references with the correct existing
task id. Keep the todo board parseable after the repair.

## Resolution

The current VAI todo board no longer contains a duplicate `VAI-200` task id.
Parsing `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
with the `ipfs_accelerate` daemon parser reports `205` tasks, `205` unique task
ids, and zero duplicate records.

The stale `VAI-200` dependency guardrail strategy block was released with the
general-purpose `ipfs_accelerate` helper after comparing stored dependency
findings against the current parsed todo board:

```text
[{'source_task_id': 'VAI-200', 'follow_up_task_id': 'VAI-204', 'guardrail_kind': 'dependency_guardrail', 'reason': 'dependency_metadata_resolved'}]
```

Validation:

```text
PYTHONPATH=external/ipfs_accelerate IPFS_ACCEL_SKIP_CORE=1 python3 - <<'PY' ... duplicate task scan ... PY
# output: tasks 205 unique 205 duplicates 0
```
