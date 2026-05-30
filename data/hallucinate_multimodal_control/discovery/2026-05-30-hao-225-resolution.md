# HAO-225 Resolution

Date: 2026-05-30
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1115
Status: resolved

## Finding

The original scan flagged line 1115 containing:

```python
clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)
```

The use of a hardcoded `'XXX'` sentinel was problematic because the literal string
`'XXX'` can appear in real error messages (e.g. from test frameworks), causing false-
positive similarity matches.

## Resolution

The fix was applied as part of VAI-144. The code was updated to use a null-byte
sentinel stored in the class attribute `_SIMILAR_SENTINEL = '\x00'`, which cannot
appear in ordinary error-message strings.

Additionally, a non-string type guard was inserted before the sentinel substitution
lines (lines 1110–1115 in the current file) to prevent `re.sub` from raising a
`TypeError` when `None` or another non-string value reaches `_messages_similar`
despite the type annotation:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

The normalisation calls now read:

```python
clean_msg1 = self._SIMILAR_PATTERN.sub(self._SIMILAR_SENTINEL, msg1)
clean_msg2 = self._SIMILAR_PATTERN.sub(self._SIMILAR_SENTINEL, msg2)
```

## Validation

- `python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` passes.
- Focused regression tests in `test/test_error_monitor.py` cover:
  - `test_none_inputs_do_not_raise` – guards against the non-string TypeError path
  - `test_message_containing_sentinel_not_falsely_similar` – verifies null-byte sentinel (VAI-144)
  - `test_two_different_hex_only_messages_not_similar` – sentinel shorter than `_SIMILAR_MIN_LEN`

## False-positive note

The scan was filed against the line numbers present before VAI-144's additions; the
relevant code has since been corrected and shifted. No further action required.
