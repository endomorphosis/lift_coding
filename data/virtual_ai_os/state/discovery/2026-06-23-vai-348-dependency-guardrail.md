# Dependency Guardrail: VAI-099

Created: 2026-06-23T17:22:17.797742+00:00
Fingerprint: 295c7a77f632754a27d6c1fe7b9e40cb48a61e3d
Source task: VAI-099 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-099
Duplicate source lines: 494, 756

## Duplicate Task Titles

- Resolve code annotation in hallucinate_app/docs/INDEX.md:24
- Resolve code annotation in hallucinate_app/docs/INDEX.md:24

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
