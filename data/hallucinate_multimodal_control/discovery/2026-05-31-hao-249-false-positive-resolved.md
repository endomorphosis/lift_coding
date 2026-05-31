# HAO-249 False Positive Resolution

Date: 2026-05-31
Fingerprint: c0b8d370e6882c1792dbe40437bf137fc39dfbb5
Kind: false_positive
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:308
Priority: P3
Track: runtime

## Finding

The codebase scanner flagged line 308 in the supervisor script:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

The scanner matched on the substring "todo" in `--objective-surplus-min-terms-per-todo`, treating it as a deferred-work annotation.

## Resolution

This is a **false positive**. The word "todo" appears as part of a CLI flag name `--objective-surplus-min-terms-per-todo`, which refers to backlog task entries in the objective surplus calculation. It is not a deferred-work annotation.

The comment on line 307 was updated to include HAO-249 in the `scanner-resolved` list:

```
# scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248, HAO-249 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

This prevents the supervisor from re-adding the same finding in future scans.
