# HAO-232 Resolution

Date: 2026-05-31
Task: HAO-232
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:304

## Finding

The codebase scanner flagged the line:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

as a code annotation because the word "todo" appears in the CLI flag name
`--objective-surplus-min-terms-per-todo`.

## Resolution

This is a false positive. The string "todo" in both the flag name and the constant
`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` refers to task-board items in the objective
surplus scoring system — not a `TODO` code annotation marker.

Two clarifying inline comments were added near the affected lines to document that
"todo" is part of the domain vocabulary (task-board items), not a code annotation:

- Line 304 (added in attempt 1): explains `--objective-todo-vector-index-path`
- Line 307 (added in attempt 2): explains `--objective-surplus-min-terms-per-todo`

No functional changes were required. The constants are correctly defined in
`hallucinate_multimodal_control_todo_daemon.py` and properly imported and wired.
