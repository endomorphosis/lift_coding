# HAO-215 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1111
Kind: code_quality_fix

## Finding

`_messages_similar` at lines 1121-1122 used a bare `and`/`or` chain without
explicit parentheses in the return statement. While Python's operator precedence
(`and` before `or`) makes it technically correct, the intent of the two independent
sub-conditions — one involving `clean_msg1`, one involving `clean_msg2` — was not
visually clear. HAO-214 (line 1110) and HAO-215 (line 1111) both flagged consecutive
lines in this same block.

## Fix

Rewrote the return statement with explicit parentheses so each sub-condition
(`len(...) >= _MIN_SUBSTRING_LEN and ... in ...`) is unambiguously grouped:

```python
return (
    (len(clean_msg1) >= _MIN_SUBSTRING_LEN and clean_msg1 in clean_msg2)
    or (len(clean_msg2) >= _MIN_SUBSTRING_LEN and clean_msg2 in clean_msg1)
)
```

This makes the `clean_msg2` branch (HAO-215) as readable as the `clean_msg1`
branch (HAO-214).

## Tests Added (TestMessagesSimilar)

- `test_msg2_substring_of_msg1_is_similar` — confirms normalised `clean_msg2` that
  appears inside `clean_msg1` is correctly detected as similar (exercises the
  second `or` branch introduced by the parentheses rewrite).
- `test_short_msg2_not_falsely_matched` — confirms the `_MIN_SUBSTRING_LEN` guard
  on the `clean_msg2` side blocks false-positive matches when normalised msg2 is
  shorter than 10 characters.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` → PASS  
`pytest hallucinate_app/test/test_error_monitor.py::TestMessagesSimilar` → 9 passed
