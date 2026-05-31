# HAO-242 Resolution

Date: 2026-05-31
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:304
Kind: annotated_followup (false positive)
Status: fixed

## Finding

The codebase scanner flagged line 304 with the comment:

```python
# Wire the task-board vector index (not a code annotation; "todo" is part of the path name).
```

The comment itself tried to clarify the intent but still triggered re-scanning because
it used a phrasing that remained ambiguous to the scanner heuristic.

## Fix

The comment was replaced (in commit a649740d, VAI-159) with a clearer form that
explicitly states "todo" is a CLI flag name component, not a deferred-work marker:

```python
# Before
# Wire the task-board vector index (not a code annotation; "todo" is part of the path name).

# After
# Pass the task-board vector-index path; "todo" here is part of the CLI flag name (work-item queue), not a deferred-work marker.
```

The adjacent line 307 was similarly updated:

```python
# "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work marker).
```

No logic change. This matches the pattern applied to other supervisor scripts
(virtual_ai_os_todo_supervisor.py, meta_glasses_display_todo_supervisor.py).

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```
Passed with exit code 0.
