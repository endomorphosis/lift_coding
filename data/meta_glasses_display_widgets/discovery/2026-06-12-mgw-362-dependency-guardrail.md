# Dependency Guardrail: MGW-242

Created: 2026-06-12T01:33:41.124235+00:00
Fingerprint: a4e42f6513d0e099f54788786e21b2220f605057
Source task: MGW-242 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: MGW-242
Duplicate source lines: 549, 567

## Duplicate Task Titles

- Resolve 14 preflight-conflicting backlogged worktree merges
- Resolve 1 preflight-conflicting backlogged worktree merges

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
