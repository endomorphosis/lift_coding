# HAO-251 False Positive Resolution

Date: 2026-05-31
Fingerprint: 35bd5e6b300e34931208d9b38cc2bc0c1e946d1b
Kind: false_positive
Source: scripts/virtual_ai_os_todo_supervisor.py:167
Priority: P3
Track: runtime

## Finding

The codebase scanner flagged line 167 in the virtual-AI-OS supervisor script:

```python
# Pass the task-board vector-index path; "todo" here is part of the CLI flag name (work-item queue), not a deferred-work marker.
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

The scanner matched on the substring "todo" in the comment and in `--objective-todo-vector-index-path`, treating it as a deferred-work annotation.

## Resolution

This is a **false positive**. The word "todo" appears as part of a CLI flag name `--objective-todo-vector-index-path`, which refers to backlog task entries (work-item queue). It is not a deferred-work annotation in the source code.

The comments at lines 167 and 170 were updated to use the `scanner-resolved` marker format:

```
# scanner-resolved: HAO-251 — "todo" in --objective-todo-vector-index-path refers to backlog task entries (CLI flag name, not a deferred-work annotation).
# scanner-resolved: HAO-251 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

Note: `scripts/` is already listed in `CODEBASE_SCAN_SKIP_PREFIXES` in both the HAO daemon and the virtual-AI-OS supervisor, so new scans should not re-flag these lines. The `scanner-resolved` marker provides an additional safeguard.
