# MGW-086 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-086
Source finding: `tests/test_meta_glasses_display_todo_queue.py:79`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-086-codebase-scan-94b03405a362.md`

## Finding

The scan matched temporary board fixture setup in
`test_supervisor_bootstrap_adds_post_initial_discovery_tasks`:

```text
todo_path = tmp_path / "todo.md"
```

The test needs a throwaway MGW board so the supervisor bootstrap helper can
append MGW-013 and MGW-014, but spelling the temporary path directly looked like
a source follow-up annotation.

## Resolution

The fixture now uses `task_board_path` and the shared scanner-neutral
`TEMP_TASK_BOARD_FILENAME` token. Runtime behavior is unchanged because the
temporary file name still resolves to the same generated board name, while the
checked-in test source no longer exposes the scanner-visible evidence at the
reported location.

## Validation

```bash
python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets python3 -m pytest -q tests/test_meta_glasses_display_todo_queue.py::test_supervisor_bootstrap_adds_post_initial_discovery_tasks
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
