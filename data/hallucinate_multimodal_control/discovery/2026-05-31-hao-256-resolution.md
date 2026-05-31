# HAO-256 Resolution

Date: 2026-05-31
Task: HAO-256
Source: scripts/virtual_ai_os_todo_supervisor.py:170

## Finding

The codebase scanner flagged a "todo" annotation at line 170 of the virtual-AI-OS
supervisor script (line numbers may have shifted due to prior scanner-resolved comment
insertions):

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Resolution

False positive. The word "todo" appears in the CLI flag name
`--objective-surplus-min-terms-per-todo`, which refers to backlog task entries
(work-item queue), not a deferred-work code annotation.

This is the same class of finding previously resolved by HAO-251 (original) and
HAO-255 (repeat after line number shift for the sibling `--objective-todo-vector-index-path`
flag). The scanner re-filed it because line numbers shifted after earlier
`scanner-resolved` comments were inserted.

The `scanner-resolved` comment was updated to include both HAO-251 and HAO-256:

```python
# scanner-resolved: HAO-251 HAO-256 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

Note: `scripts/` is already listed in `CODEBASE_SCAN_SKIP_PREFIXES` in the supervisor,
so new scans should not re-flag these lines. The updated `scanner-resolved` marker
provides an additional safeguard against repeat filings.
