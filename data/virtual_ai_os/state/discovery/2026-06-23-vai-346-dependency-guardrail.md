# Dependency Guardrail: VAI-097

Created: 2026-06-23T17:22:17.797045+00:00
Fingerprint: 24dca20e4cede7b9806c84329eb4b19445300034
Source task: VAI-097 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: VAI-097
Duplicate source lines: 490, 732

## Duplicate Task Titles

- Resolve code annotation in work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180
- Resolve code annotation in work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180

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
