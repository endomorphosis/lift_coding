# HAO-190 Resolution: False Positive Annotation at supervisor.py:303

Date: 2026-05-28
Task: HAO-190
Source finding: 2026-05-28-hao-190-codebase-scan-fbd7ce184cdf.md

## Finding

The codebase scanner flagged line 303 of
`scripts/hallucinate_multimodal_control_todo_supervisor.py` as an
`annotated_followup` because the line contains the substring "todo" inside the
argument name `--objective-surplus-min-terms-per-todo` and in the constant
`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO`.

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Assessment: False Positive

`OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` is a module-level constant imported from
`hallucinate_multimodal_control_todo_daemon.py`. The word "todo" in the name
refers to task-board items (todos in the backlog), **not** a `# TODO` code
annotation. The line is correct runtime configuration wiring that passes the
minimum search-term threshold to the objective surplus scanner.

## Fix Applied

A clarifying inline comment was added immediately above the line so the scanner
can distinguish it from an actual code annotation on future scans:

```python
# Wire surplus min-terms threshold (not a code annotation; "todo" refers to task-board items).
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exits 0 — no compilation errors introduced.
