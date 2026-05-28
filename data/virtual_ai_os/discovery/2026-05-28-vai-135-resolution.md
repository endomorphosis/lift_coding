# VAI-135 Resolution Notes

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1111

## What was done

The annotated followup at line 1111 (`clean_msg2 = self._SIMILAR_PATTERN.sub(...)`)
was the final outstanding item after a prior fix added the non-string guard
(lines 1101-1106).  The remaining maintenance risk was:

1. `_MIN_SUBSTRING_LEN` defined as a method-local magic constant — moved to
   `_SIMILAR_MIN_LEN` class attribute next to `_SIMILAR_PATTERN`.
2. Implicit `and`/`or` precedence in the `return` expression — replaced with
   explicit parentheses so the logic is unambiguous without needing to recall
   Python precedence rules.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
# exit 0
```

## False-positive assessment

Not a false positive — the operator-precedence ambiguity and inline magic
constant were genuine maintenance risks that warranted a small cleanup.
