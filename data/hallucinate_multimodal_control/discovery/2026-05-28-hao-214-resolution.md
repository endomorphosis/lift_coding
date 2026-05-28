# HAO-214 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1110
Kind: code_quality_fix

## Finding

`_messages_similar` at line 1121-1122 used a bare `and`/`or` chain without
explicit parentheses, making the operator-precedence intent unclear to readers
even though Python's rules (`and` before `or`) make it technically correct.

## Fix

Added explicit parentheses to the return statement so the two sub-conditions
(`len(...) >= _MIN_SUBSTRING_LEN and ... in ...`) are unambiguously grouped.

## Tests Added (TestMessagesSimilar)

- `test_substring_match_after_normalisation` — confirms a shorter normalised
  string that is a prefix of the longer is still matched as similar.
- `test_short_normalised_message_not_falsely_matched` — confirms the
  `_MIN_SUBSTRING_LEN` guard blocks false substring matches when the normalised
  form is fewer than 10 characters.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py` → PASS  
`pytest hallucinate_app/test/test_error_monitor.py::TestMessagesSimilar` → 9 passed
