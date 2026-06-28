# Dependency Guardrail: VAI-096

Created: 2026-06-23T17:22:17.796686+00:00
Fingerprint: 953c0e7e7c01279cf96560542037e660b594975d
Source task: VAI-096 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-096
Duplicate source lines: 488, 721

## Duplicate Task Titles

- Resolve code annotation in work/PR-090-agent-runner-docs-sync.md:1
- Resolve code annotation in work/PR-090-agent-runner-docs-sync.md:1

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
