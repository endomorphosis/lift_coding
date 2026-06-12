# Dependency Guardrail: VAI-214

Created: 2026-06-12T03:03:57.044964+00:00
Fingerprint: a2d21a2eac41bdc829b9a4c75ace386b3a833efb
Source task: VAI-214 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-214
Duplicate source lines: 511, 825

## Duplicate Task Titles

- Review swallowed exception path in external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245
- Resolve merge retry-budget failure for VAI-155

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
