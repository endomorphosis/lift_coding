# Dependency Guardrail: VAI-095

Created: 2026-06-23T17:22:17.796225+00:00
Fingerprint: 4ad8380d41510bf464472058f38d4931838c230f
Source task: VAI-095 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-095
Duplicate source lines: 486, 710

## Duplicate Task Titles

- Resolve code annotation in work/PR-081-privacy-mode-per-profile.md:18
- Resolve code annotation in work/PR-081-privacy-mode-per-profile.md:18

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
