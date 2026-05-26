# Dependency Guardrail: MGW-049

Created: 2026-05-26T19:00:06.909601+00:00
Fingerprint: 78d0c5daf2a2605b0e201ec8d33b6e162c7dc043
Source task: MGW-049 Duplicate task id
Missing dependencies: none
Self-referential dependencies: none
Dependency cycle: none
Duplicate task id: MGW-049
Duplicate source lines: 559, 587

## Duplicate Task Titles

- Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:110
- Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:110

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
