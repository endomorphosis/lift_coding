# HAO-216 Resolution (Attempt 4)

Date: 2026-06-09
Task: HAO-216
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118
Kind: annotated_followup → resolved (confirmed)

## Finding

The codebase scanner flagged line 1118 with this fragment:

```python
# that was entirely a hex address and became "XXX") would otherwise cause
```

This was a dangling comment fragment in `_messages_similar` where `"XXX"` was
used as the sentinel placeholder string.  The original logic gap: the equality
branch of `_messages_similar` (`if clean_msg1 == clean_msg2: return True`)
had no minimum-length guard, so two distinct single-token volatile messages
(e.g. bare hex addresses `"0xDEAD"` and `"0xBEEF"`) that both normalised to
the same short sentinel were incorrectly treated as duplicate errors.

## Status

All prior fix work was already committed to the submodule branch
`implementation/hao-216-attempt-4-1780992087-submodule-hallucinate_app` by
earlier attempts.  Attempt 4 confirms the implementation is complete and
validates it.

## Fix Confirmed In Place

`_SIMILAR_SENTINEL` is defined as `'\x00'` (null byte) rather than `"XXX"`.
The null byte cannot appear in ordinary error-message strings, preventing
false-positive similarity matches (VAI-144).  The equality branch now applies
the same `_SIMILAR_MIN_LEN` guard as the substring branches:

```python
_SIMILAR_SENTINEL = '\x00'
_SIMILAR_MIN_LEN = 10

if clean_msg1 == clean_msg2 and len(clean_msg1) >= self._SIMILAR_MIN_LEN:
    return True
return (
    (len(clean_msg1) >= self._SIMILAR_MIN_LEN and clean_msg1 in clean_msg2)
    or (len(clean_msg2) >= self._SIMILAR_MIN_LEN and clean_msg2 in clean_msg1)
)
```

A type guard at the top of the method prevents `re.sub` from raising
`TypeError` when non-string values reach this function despite the annotation:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

An identical-message early-return (`if msg1 == msg2: return True`) handles
genuine duplicates before the min-length guard, ensuring real duplicates are
never blocked by the length check.

## Tests

Two focused regression tests (tagged HAO-216) are present in
`hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`:

- `test_equality_branch_requires_min_len`: two messages consisting entirely of a
  volatile token (e.g. different bare timestamps) normalise to the single
  null-byte sentinel (length 1 < 10); must NOT be treated as similar.
- `test_equality_branch_passes_with_long_normalised_string`: two messages that
  differ only in a hex address normalise to the same long static string (length
  > 10); must be treated as similar.

Both tests pass.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes with exit code 0.
