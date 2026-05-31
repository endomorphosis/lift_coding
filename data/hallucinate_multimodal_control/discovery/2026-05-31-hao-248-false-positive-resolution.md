# HAO-248 Resolution: False Positive

Date: 2026-05-31
Task: HAO-248
Kind: false_positive_resolution

## Finding

The codebase scanner flagged `scripts/hallucinate_multimodal_control_todo_supervisor.py:307`
because the word "todo" appears on that line. The existing `scanner-resolved` comment
(citing MGW-191, MGW-192, HAO-244) already explained that "todo" in
`--objective-surplus-min-terms-per-todo` is part of a CLI flag name (backlog task entry
count threshold), not a deferred-work annotation.

## Resolution

Updated the `scanner-resolved` annotation on line 307 to include HAO-248:

```
# scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

This prevents the scanner from re-filing the same false positive in future runs.

## Validation

`python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py` → OK
