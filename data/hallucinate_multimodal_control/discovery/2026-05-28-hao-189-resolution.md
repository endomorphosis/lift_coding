# HAO-189 Resolution: False Positive Annotation at supervisor.py:301

Date: 2026-05-28
Task: HAO-189
Source finding: 2026-05-28-hao-189-codebase-scan-7d52a8f929c8.md

## Finding

The codebase scanner flagged line 301 of
`scripts/hallucinate_multimodal_control_todo_supervisor.py` as an
`annotated_followup` because the line contains the substring "todo" inside the
variable name `OBJECTIVE_TODO_VECTOR_INDEX_PATH`.

```python
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

## Assessment: False Positive

`OBJECTIVE_TODO_VECTOR_INDEX_PATH` is a module-level constant imported from
`hallucinate_multimodal_control_todo_daemon.py`.  It resolves to:

```
data/hallucinate_multimodal_control/objective_bundles/todo_vector_index.json
```

The word "todo" in the name refers to the task-board (todo-list) vector index
file used by the objective-refill scanner, **not** a `# TODO` code annotation.
The line is correct runtime configuration wiring and carries no technical debt.

## Fix Applied

A clarifying inline comment was added immediately above the line so the scanner
can distinguish it from an actual code annotation on future scans:

```python
# Wire the task-board vector index (not a code annotation; "todo" is part of the path name).
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exits 0 — no compilation errors introduced.
