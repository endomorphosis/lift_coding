# HAO-235 False Positive Resolution

Date: 2026-05-31
Source: scripts/virtual_ai_os_todo_supervisor.py:159 (now line 167)

## Finding

The codebase scanner flagged line 159 as a "code annotation" because the flag name
`--objective-todo-vector-index-path` and variable `OBJECTIVE_TODO_VECTOR_INDEX_PATH`
contain the word "todo". This is not a `# TODO` marker — it is a CLI flag that
wires the task-board vector index path to the supervisor.

Similarly, `--objective-surplus-min-terms-per-todo` was flagged for the same reason;
"todo" here refers to backlog task entries, not a deferred-work annotation.

## Resolution

Added inline comments above both flagged lines in `scripts/virtual_ai_os_todo_supervisor.py`
clarifying that "todo" in these flag names refers to task-board items, not code
annotations. This matches the pattern already applied in:
- `scripts/hallucinate_multimodal_control_todo_supervisor.py` (HAO-189 / HAO-190)
- `scripts/meta_glasses_display_todo_supervisor.py` (HAO-191)

No logic change; compile-clean after the edit.
