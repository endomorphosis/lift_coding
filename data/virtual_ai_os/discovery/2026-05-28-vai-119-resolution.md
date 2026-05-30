# VAI-119 Resolution

Date: 2026-05-28
Source finding: 2026-05-28-vai-119-codebase-scan-5feefc7cd9b2.md
Kind: false_positive

## Summary

Lines 301 and 304 in `scripts/hallucinate_multimodal_control_todo_supervisor.py`
contained meta-comments explaining that the `--objective-{task-board}-vector-index-path` and
`--objective-surplus-min-terms-per-{task-board}` flag names embed the board-name segment as
part of the flag identifier, not as a code annotation. These comments were themselves
triggering the codebase scanner on every run.

The fix removes the two redundant comments. The `_with_default` calls are
self-explanatory; the flag names match the imported constants directly and need no
clarifying prose.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0.
