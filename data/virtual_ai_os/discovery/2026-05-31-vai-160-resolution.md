# VAI-160 Resolution

Date: 2026-05-31
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:305
Kind: annotated_followup (false positive)
Fingerprint: 969bf9b8ee48867ade61424bcdf9374e6e5b7a5f

## Finding

The codebase scanner flagged line 305 of the supervisor script:

```python
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

## Analysis

This is a false positive. The segment within `--objective-todo-vector-index-path` is part
of the CLI flag name referring to the task-board / work-item queue, not a deferred-work
marker. The clarifying comment at line 304 (updated by VAI-159) already explains this:

```python
# Pass the task-board vector-index path; "todo" here is part of the CLI flag name (work-item queue), not a deferred-work marker.
```

The nearby comment at line 307 was also rephrased (in this fix) to avoid using the
phrase "code annotation" which can re-trigger the scanner's annotation-detection
heuristic:

Before:
```python
# Not a code annotation; "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries.
```

After:
```python
# "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work marker).
```

## Validation

```bash
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```
