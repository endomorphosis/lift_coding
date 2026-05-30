# HAO-227 Resolution Notes

Date: 2026-05-30
Task: HAO-227 Resolve code annotation in error_monitor.py:1121
Source finding: 2026-05-30-hao-227-codebase-scan-f2f5d5fa5a3e.md

## Finding Summary

The codebase scan flagged line 1121 of error_monitor.py containing:
```
# normalising to the three-character token "XXX") are not conflated.
```

This comment was stale — it described an older sentinel value (`'XXX'`, 3 chars)
that was replaced with a null byte (`'\x00'`, 1 char) when VAI-144 fixed a
false-positive similarity risk (literal "XXX" could appear in real error strings
from test frameworks, causing unrelated errors to be conflated).

## Resolution

VAI-144 had already:
1. Changed `_SIMILAR_SENTINEL` from `'XXX'` to `'\x00'`
2. Updated the comment at the call site to say "one-character sentinel"
3. Added a test (`test_message_containing_sentinel_not_falsely_similar`) verifying
   the sentinel identity

HAO-227 adds a dedicated regression test
`test_sentinel_is_single_null_byte_not_xxx` in `TestMessagesSimilar` that:
- Asserts `len(sentinel) == 1`
- Asserts `sentinel == '\x00'`
- Asserts `sentinel != 'XXX'`
- Re-verifies that two distinct volatile-only messages are not conflated

## Status

False positive (already fixed by VAI-144). Focused validation added to prevent
the scan from re-filing the same finding. The annotation text no longer exists
in the codebase.
