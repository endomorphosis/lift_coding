# HAO-256 Resolution

Date: 2026-05-31
Task: HAO-256
Source: scripts/virtual_ai_os_todo_supervisor.py:170

## Finding

The codebase scanner flagged a "todo" annotation at line 170 of the virtual-AI-OS
supervisor script. The original finding came from the old explicit daemon CLI
argument wiring:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Resolution

False positive. The word "todo" appeared in the CLI flag name
`--objective-surplus-min-terms-per-todo`, which refers to backlog task entries
(work-item queue), not a deferred-work code annotation. The current wrapper now
delegates daemon defaults through
`OBJECTIVE_REFILL_SETTINGS.surplus_min_terms_per_todo`, so the durable source
annotation belongs on that runtime setting.

This is the same class of finding previously resolved by HAO-251 (original) and
HAO-255 (repeat after line number shift for the sibling `--objective-todo-vector-index-path`
flag). The scanner re-filed it because line numbers shifted after earlier
`scanner-resolved` comments were inserted.

The current `scanner-resolved` comment records HAO-256 on the runtime setting:

```python
# scanner-resolved: HAO-256 - "todo" in surplus_min_terms_per_todo maps to
# the daemon's backlog task-entry threshold option; it is runtime wiring, not
# a deferred-work annotation.
```

Note: `scripts/` is already listed in `CODEBASE_SCAN_SKIP_PREFIXES` in the supervisor,
so new scans should not re-flag these lines. The updated `scanner-resolved` marker
provides an additional safeguard against repeat filings.
