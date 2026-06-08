# VAI-170 False Positive Resolution

Date: 2026-05-31
Fingerprint: 4da5e8f2f5fec326715246a958c71b3fb8ddb64a
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Resolution: false_positive

## Summary

The scanner flagged line 307 of `scripts/hallucinate_multimodal_control_todo_supervisor.py`
which already contained a `scanner-resolved` annotation explaining that the CLI
flag name `--objective-surplus-min-terms-per-todo` refers to backlog task entries, not a
deferred-work annotation.

This is the same recurring false positive previously resolved as MGW-191, MGW-192, HAO-244,
HAO-248, HAO-249, VAI-166, and HAO-254. The scanner keeps re-flagging the `scanner-resolved`
comment itself because the comment text contains "todo" (as part of the CLI flag name).

## Action Taken

Added VAI-170 to the scanner-resolved comment at line 307 to prevent future re-flagging:

```python
# scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248, HAO-249, VAI-166, HAO-254, VAI-170 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

## Validation

`python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py` — passes.
