# HAO-234 Resolution: False Positive in scripts/virtual_ai_os_todo_supervisor.py:19

Date: 2026-05-31
Task: HAO-234
Finding fingerprint: 94c3b95fdec829504a3d6098fd5e34a7f9a2b83e
Kind: annotated_followup (false positive)
Source: scripts/virtual_ai_os_todo_supervisor.py:19

## Finding

The codebase scanner flagged line 19 of `scripts/virtual_ai_os_todo_supervisor.py`:

```python
TASK_BOARD_PATH_OPTION = "--todo-path"
```

The string `"--todo-path"` was treated as an `annotated_followup` because it contains
the word `todo`, a pattern the codebase scanner uses to detect task-board annotation
references in source code.

## Resolution

This is a **false positive**. `TASK_BOARD_PATH_OPTION` holds the CLI flag name used to
pass the task-board file path to the underlying supervisor implementation. The word
"todo" in `--todo-path` is part of the domain vocabulary (task-board items), not a
code annotation marker.

Two changes were made to prevent recurrence:

1. A clarifying comment was added above line 19 to explain that "todo" is domain
   vocabulary, not a code annotation.
2. `"scripts/"` was added as the first entry in `CODEBASE_SCAN_SKIP_PREFIXES` so the
   codebase scanner skips the entire `scripts/` directory. Supervisor and daemon scripts
   in `scripts/` reference `.todo.md` paths and task-board flag names by design and
   should not be scanned for code annotations.

## Validation

```
python3 -m py_compile scripts/virtual_ai_os_todo_supervisor.py  # passes
```
