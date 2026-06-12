# Dependency Guardrail: MGW-241

Created: 2026-06-12T01:33:41.123995+00:00
Fingerprint: 7e42b9599a7922dfea7f46109b5d7d87edf66b3c
Source task: MGW-241 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: MGW-241
Duplicate source lines: 547, 554

## Duplicate Task Titles

- Resolve 2 dirty backlogged worktrees blocked by unsupported_status
- Resolve 2 dirty backlogged worktrees blocked by unsupported_status

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
