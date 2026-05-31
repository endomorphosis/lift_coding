# MGW-178 Resolution

Date: 2026-05-31
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:301
Evidence: data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-178-codebase-scan-7d52a8f929c8.md
Fingerprint: 7d52a8f929c8ecd6a5d978f10f46758dddd1a331

## Finding

The codebase scanner flagged the following line in
`scripts/hallucinate_multimodal_control_todo_supervisor.py`:

```python
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

The scanner treated the substring `todo` in `--objective-todo-vector-index-path` as an
annotated follow-up marker, inferring an unresolved code annotation.

## Resolution

This is a **false positive**. The argument name `--objective-todo-vector-index-path` refers
to the file-system path of the task-board vector index (`OBJECTIVE_TODO_VECTOR_INDEX_PATH`).
The word "todo" is part of the canonical path/argument name used by the objective scanner
subsystem and does not annotate any incomplete work.

A clarifying comment was added immediately above the line (now line 305 after unrelated
upstream edits shifted numbering) to document this for future scans:

```python
# Wire the task-board vector index (not a code annotation; "todo" is part of the path name).
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

<!-- scanner-resolved: MGW-178 — "--objective-todo-vector-index-path" is a CLI argument name referencing the task-board vector index path; "todo" is not a code annotation -->

## Status

False positive suppressed via inline comment. No functional change to runtime behaviour.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0 — file compiles cleanly.
