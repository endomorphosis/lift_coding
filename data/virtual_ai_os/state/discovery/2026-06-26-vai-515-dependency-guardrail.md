# Dependency Guardrail: VAI-203

Created: 2026-06-26T02:03:32.420126+00:00
Fingerprint: e4164f6c5221735082ddb010e07470520702876d
Source task: VAI-203 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-203
Duplicate source lines: 1744, 1746

## Duplicate Task Titles

- Resolve 5 preflight-conflicting backlogged worktree merges
- Resolve 4 preflight-conflicting backlogged worktree merges

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
