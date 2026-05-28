# HAO-192 Resolution: False Positive Annotation at meta_glasses_display_todo_supervisor.py:304

Date: 2026-05-28
Task: HAO-192
Source finding: 2026-05-28-hao-192-codebase-scan-8461e40bbb4a.md

## Finding

The codebase scanner flagged line 304 of
`scripts/meta_glasses_display_todo_supervisor.py` as an `annotated_followup`
because the line contained the substring "todo" inside the argument name
`--objective-surplus-min-terms-per-todo` and the constant
`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO`:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Assessment: False Positive

`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` is a module-level constant defined in the
supervisor. The word "todo" in the name refers to task-board items (todos in the
backlog), **not** a `# TODO` code annotation. The line is correct runtime
configuration wiring that passes the minimum search-term threshold to the
objective surplus scanner.

## Fix Applied

A clarifying inline comment was added immediately above the flagged line by
VAI-116 so the scanner can distinguish it from an actual code annotation on
future scans. The parallel `--objective-todo-vector-index-path` line at 303
received the same treatment in the same commit:

```python
# Wire the task-board vector index (not a code annotation; "todo" is part of the path name).
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
args = _with_default(args, "--objective-surplus-findings-per-goal", str(OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL))
# Wire surplus min-terms threshold (not a code annotation; "todo" refers to task-board items).
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

This matches the pattern applied in
`scripts/hallucinate_multimodal_control_todo_supervisor.py` for HAO-190.
No logic changes were made.

## Validation

```
python3 -m py_compile scripts/meta_glasses_display_todo_supervisor.py
```

Exits 0 — no compilation errors introduced.
