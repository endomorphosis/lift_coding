# VAI-140 Resolution Note

Date: 2026-05-30
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1112
Finding: annotated_followup for `clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)`

## Assessment

The finding is a **false positive / already fixed**. The code at line 1112 is
safe because of the type guard introduced at lines 1106-1107:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

This guard ensures that `re.sub` is only called after both `msg1` and `msg2` are
confirmed to be `str` instances. Additionally, `_SIMILAR_PATTERN` (defined at
line 787) uses `re.IGNORECASE` so uppercase hex tokens like `0xDEADBEEF` are
normalised identically to lowercase variants.

## Action Taken

Added two focused tests to `TestMessagesSimilar` in `test_error_monitor.py`:

1. `test_similarity_is_symmetric` (VAI-140): Confirms that swapping msg1 and msg2
   produces the same result, exercising the `clean_msg2` branch symmetrically.

2. `test_clean_msg2_type_guard_blocks_non_string` (VAI-140): Directly proves that
   non-string msg2 values never reach `_SIMILAR_PATTERN.sub`, validating that
   the type guard at lines 1106-1107 is effective.

## Validation

All 19 tests pass:
  python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
  python3 -m pytest hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py -v
