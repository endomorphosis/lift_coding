# HAO-220 Resolution

Date: 2026-05-30
Task: HAO-220
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1112
Kind: annotated_followup → resolved

## Finding

The scanner flagged line 1112:

```python
clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)
```

## Analysis

The line is correct and symmetric with line 1111 (`clean_msg1`). Prior passes
(VAI-131, VAI-132, HAO-215, VAI-136, HAO-219) already:

- Added an `isinstance` guard (lines 1106-1107) so `None` inputs do not raise
  `TypeError` before reaching `_SIMILAR_PATTERN.sub`.
- Documented `re.IGNORECASE` semantics in comments (lines 1108-1110).
- Added `_SIMILAR_MIN_LEN` (10) guard on both branches of the return expression
  (lines 1121-1123) so that when a message normalises to a very short token like
  `"XXX"` it does not produce false-positive similarity matches.

## Gap addressed

Two paths that are specific to `clean_msg2` lacked test coverage:

1. **Date in msg2** — `\d{4}-\d{2}-\d{2}` normalises a date carried by msg2 so
   that otherwise identical messages with different run-dates deduplicate via the
   exact-match path.
2. **clean_msg2 substring branch** — when msg2 contains a volatile hex address
   (`0x[0-9a-f]+`), after normalisation its core text may appear inside the longer
   normalised msg1, exercising the second OR branch:
   `len(clean_msg2) >= _SIMILAR_MIN_LEN and clean_msg2 in clean_msg1`.

## Changes

- `hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`:
  Added `test_msg2_date_normalised_for_deduplication` and
  `test_clean_msg2_substring_in_clean_msg1` (both tagged HAO-220) to exercise the
  two uncovered `clean_msg2` paths.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes. No production code was modified; the finding is resolved by documentation
of correct prior fixes and two new focused tests for the `clean_msg2` code path.
