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

The current supervisor no longer embeds the flagged
`--objective-surplus-min-terms-per-todo` literal. Objective-refill CLI defaults are
now produced through `build_namespace_objective_refill_defaults_factory(...)`, with
the namespace settings passed via `OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs()`.
An inline `scanner-resolved: HAO-232` comment was added at that factory wiring point
so future scans can associate the stale finding with the shared-defaults migration.

No functional changes were required. The task-board terminology remains valid, and
the supervisor-fed backlog remains parseable.
