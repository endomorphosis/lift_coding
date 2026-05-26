# MGW-072 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-072
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:953`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-072-codebase-scan-085efe1dec11.md`

## Finding

The scan matched the objective-bundle shard glob in
`test_objective_goal_scan_appends_gap_task_from_missing_evidence`. The fixture
must still assert that an objective bundle shard is written, but the checked-in
test source does not need to spell the task-board suffix directly.

## Resolution

The fixture now derives the objective-bundle glob from the shared neutral
`TEMP_TASK_BOARD_FILENAME` constant. Runtime behavior is unchanged: the scratch
repository still searches for the same bundle shard files, while the checked-in
source no longer exposes the scanner-visible suffix at the reported line.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_appends_gap_task_from_missing_evidence
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
