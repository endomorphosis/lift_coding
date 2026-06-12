# Dependency Guardrail: MGW-239

Created: 2026-06-12T01:01:08.056840+00:00
Fingerprint: 29a2071dfddd77d4d1c51c0dda632cd78ee1e885
Source task: MGW-239 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: MGW-239
Duplicate source lines: 494, 499

## Duplicate Task Titles

- Resolve dirty main checkout blocking 17 worktree merges
- Resolve dirty main checkout blocking 5 worktree merges

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
