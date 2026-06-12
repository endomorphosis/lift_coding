# Dependency Guardrail: VAI-201

Created: 2026-06-12T01:14:04.405500+00:00
Fingerprint: db490e8e63b45c93846e512d8e8c8e0268626932
Source task: VAI-201 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-201
Duplicate source lines: 433, 448

## Duplicate Task Titles

- Resolve 63 dirty backlogged worktrees blocked by content_not_in_target
- Resolve 1 dirty backlogged worktrees blocked by content_not_in_target

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
