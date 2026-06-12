# Dependency Guardrail: MGW-239

Created: 2026-06-12T02:57:01.307867+00:00
Fingerprint: 32a445bae94299685f42bb0a3b98fb30c36ab5e2
Source task: MGW-239 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: MGW-239
Duplicate source lines: 2646, 2648

## Duplicate Task Titles

- Resolve dirty main checkout blocking 24 worktree merges
- Resolve dirty main checkout blocking 11 worktree merges

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
