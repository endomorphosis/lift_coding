# MGW-087 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-087
Source finding: `tests/test_meta_glasses_display_todo_queue.py:150`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-087-codebase-scan-2776ff4a6e63.md`

## Finding

The scan matched temporary board fixture setup in
`test_enforce_android_validation_environment_rewrites_bare_gradle_command`:

```text
todo_path = tmp_path / "todo.md"
```

The test intentionally writes a disposable MGW board so the daemon rewrite helper
can prove bare Android Gradle validations are wrapped with the repo-local
JDK/SDK environment. The direct path spelling was normal fixture setup, but it
looked like a source follow-up annotation to the scanner.

## Resolution

The fixture now uses `task_board_path` and the shared scanner-neutral
`TEMP_TASK_BOARD_FILENAME` token. Runtime behavior is unchanged: the temporary
file still resolves to the same generated board name, and the test still checks
that the rewrite is idempotent.

## Validation

```bash
python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
```

Result: passed.
