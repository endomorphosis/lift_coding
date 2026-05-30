# HAO-224 Resolution

Date: 2026-05-30
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1114
Status: resolved

## Finding

The scan flagged line 1114 containing:

```python
clean_msg1 = self._SIMILAR_PATTERN.sub('XXX', msg1)
```

The hardcoded `'XXX'` sentinel was problematic because the literal string `'XXX'`
can appear in real error messages (e.g. from test frameworks), causing false-positive
similarity matches when a volatile token in one message normalises to `'XXX'` and that
string also appears verbatim in another message's static text.

## Resolution

The fix was applied as part of VAI-144.  Both `clean_msg1` and `clean_msg2`
substitution calls now use the class attribute `_SIMILAR_SENTINEL = '\x00'` (a null
byte), which cannot appear in ordinary error-message strings, eliminating the
false-positive risk:

```python
clean_msg1 = self._SIMILAR_PATTERN.sub(self._SIMILAR_SENTINEL, msg1)
clean_msg2 = self._SIMILAR_PATTERN.sub(self._SIMILAR_SENTINEL, msg2)
```

A non-string type guard was also added before the substitution lines so that `None`
or another non-string value reaching `_messages_similar` (despite the type annotation)
does not cause `re.sub` to raise a `TypeError`:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

## Validation

- `python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` passes.
- Focused regression tests in `test/test_error_monitor.py` cover:
  - `test_none_inputs_do_not_raise` – guards against the non-string TypeError path
  - `test_message_containing_sentinel_not_falsely_similar` – verifies null-byte sentinel (VAI-144)
  - `test_two_different_hex_only_messages_not_similar` – sentinel shorter than `_SIMILAR_MIN_LEN`

## False-positive note

The scan was filed against the line numbers present before VAI-144's additions; the
relevant code has since been corrected and the line numbers have shifted. No further
code change is required.
