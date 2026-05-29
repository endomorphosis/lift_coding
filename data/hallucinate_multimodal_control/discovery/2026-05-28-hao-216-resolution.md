# HAO-216 Resolution Notes

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1118

## Finding

The `_messages_similar` method (line 1100) had a logic gap: the equality check
at line 1115 (`if clean_msg1 == clean_msg2: return True`) was applied without
the same min-length guard used by the subsequent substring check.

Two distinct messages that normalise to the same *short* string — e.g. bare hex
addresses `"0xDEAD"` and `"0xBEEF"` both becoming `"XXX"` — were incorrectly
treated as similar, collapsing unrelated error events into the same duplicate
bucket.

## Fix

Applied the `_SIMILAR_MIN_LEN` guard to the equality branch as well.  An
identical *original* message (genuine duplicate) still matches regardless of
length; only the case where different originals normalise to the same short
string is now correctly rejected.

```python
if clean_msg1 == clean_msg2:
    if len(clean_msg1) >= self._SIMILAR_MIN_LEN or msg1 == msg2:
        return True
```

## Tests Added (HAO-216)

- `test_two_different_bare_addresses_not_similar` — distinct hex addresses must
  not be considered similar after normalisation.
- `test_identical_bare_address_is_similar` — the same bare address repeated IS
  a genuine duplicate and must still match.
