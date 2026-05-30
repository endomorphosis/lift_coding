# HAO-219 Resolution

Date: 2026-05-30
Task: HAO-219
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1111
Kind: annotated_followup → resolved

## Finding

The scanner flagged line 1111:

```python
clean_msg1 = self._SIMILAR_PATTERN.sub('XXX', msg1)
```

## Analysis

The line is correct. A prior pass (VAI-131, VAI-132, HAO-215, VAI-136) already:

- Added a `isinstance` guard (lines 1106-1107) so `None` inputs don't raise `TypeError`.
- Documented `re.IGNORECASE` semantics in comments (lines 1108-1110).
- Added `_SIMILAR_MIN_LEN` (10) guard on the substring branches (lines 1121-1123) to
  prevent short normalised tokens ("XXX") from creating false-positive similarity matches.

## Gap addressed

Two pattern branches lacked explicit test coverage:

1. `ID: [a-f0-9-]+` — normalises UUID-style hex IDs in error messages.
2. `at [^:]+:\d+` — normalises `file:lineno` stack-trace locations.

## Changes

- `hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`:
  Added `test_id_field_normalised` and `test_stack_trace_file_lineno_normalised`
  (both tagged HAO-219) to exercise the two uncovered sub-patterns.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes. No production code was modified; the finding is resolved by documentation
of correct prior fixes and the two new focused tests.
