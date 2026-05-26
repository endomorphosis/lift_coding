# MGW-071 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-071
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:917`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-071-codebase-scan-e2226ae85245.md`

## Finding

The scan matched a hard-coded `todo.md` path in
`test_objective_goal_scan_appends_gap_task_from_missing_evidence`. The test
already creates its scratch task board through `TEMP_TASK_BOARD_FILENAME`, so the
git fixture should stage that same runtime filename instead of repeating the
literal task-board path.

## Resolution

The fixture now derives all staged fixture paths from the `Path` objects created
by the test when seeding the temporary git repository. Runtime behavior is
unchanged, and the checked-in test source no longer exposes the scanner-visible
literal at the reported line.

The merge resolution also preserves the implementation branch's generated VAI
follow-up tasks in the virtual-AI-OS todo board, with empty dependency lines
normalized to the existing task-board format.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_appends_gap_task_from_missing_evidence -q
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
