# VAI-145 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: 476c9d2eeaeaf5b5d48a9896d610753eb2626c84
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1115
Priority: P2
Track: runtime

## Evidence

```text
clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (VAI-145)

**Status: Resolved — False positive; upstream fix already applied.**

The evidence line was the historical content of line 1115 before VAI-144 rewrote
`_messages_similar`.  The current implementation at that line is:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

This isinstance guard prevents `re.sub` from receiving a non-string argument
(which would raise `TypeError`) and was introduced as part of the VAI-144 fix.
The hardcoded `'XXX'` sentinel referenced in the evidence has been replaced
throughout by `self._SIMILAR_SENTINEL` (the null byte `'\x00'`), which is also
shorter than `_SIMILAR_MIN_LEN` to prevent false-positive deduplication of
entirely-volatile messages.

A focused regression test `test_non_string_type_guard_at_line_1115` has been
added to `test/test_error_monitor.py` (VAI-145) to document and lock in the
correct behaviour of the type guard.
