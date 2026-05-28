# HAO-191 False Positive Resolution

Date: 2026-05-28
Source: scripts/meta_glasses_display_todo_supervisor.py:302

## Finding

The codebase scanner flagged line 302 as a "code annotation" because the flag name
`--objective-todo-vector-index-path` contains the word "todo".  This is not a
`# TODO` marker — it is a CLI flag that wires the task-board vector index path
to the supervisor.

## Resolution

Added an inline comment above the flagged line (and the parallel
`--objective-surplus-min-terms-per-todo` line at 304) clarifying that "todo" in
these flag names refers to task-board items, not code annotations.  This matches
the pattern already applied in `scripts/hallucinate_multimodal_control_todo_supervisor.py`
(HAO-189 / HAO-190).

No logic change; compile-clean after the edit.
