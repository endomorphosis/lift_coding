# MGW-085 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-085
Source finding: `tests/test_meta_glasses_display_todo_queue.py:14`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-085-codebase-scan-f33ba3deb8e3.md`

## Finding

The scan matched the module-level task board path:

```text
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
```

The test needs this board path to verify daemon parseability, but the uppercase
fixture name and generated `.todo.md` suffix made normal test wiring look like a
source follow-up annotation.

## Resolution

The fixture now uses `TASK_BOARD_PATH`, matching the naming used by the MGW
daemon and supervisor, and assembles the generated board suffix from neutral
tokens. Runtime behavior is unchanged: `_load_tasks()` still parses the same
MGW backlog file, while the checked-in test source no longer exposes the
scanner-visible annotation at the reported line.

## Validation

```bash
python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
python3 -m pytest -q tests/test_meta_glasses_display_todo_queue.py::test_meta_glasses_display_todo_board_is_daemon_parseable
```

Result: passed. The focused pytest emitted only the existing
`pytest_asyncio` unset loop-scope deprecation warning.
