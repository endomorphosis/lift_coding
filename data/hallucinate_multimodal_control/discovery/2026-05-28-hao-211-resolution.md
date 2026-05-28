# HAO-211 Resolution: _messages_similar clean_msg2 type-safety (already fixed by HAO-210)

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1103
Status: fixed

## Findings

The scan filed HAO-211 pointing at the former line 1103:

```python
clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)
```

This was the mirror of the HAO-210 finding at line 1102 (`msg1`).  Both lines
were vulnerable to a `TypeError` when a non-string value reached `re.sub` at
runtime despite the `str` type annotation.

## Resolution

The isinstance guard added in HAO-210 already covers both arguments:

```python
if not isinstance(msg1, str) or not isinstance(msg2, str):
    return msg1 == msg2
```

This short-circuits before either `re.sub` call, so the `msg2` path (the
original HAO-211 evidence) is also protected.

## Additional improvement (this PR)

Explicit parentheses were added to the substring-match return expression for
clarity.  The operator precedence was already correct (`and` binds tighter than
`or`), but without explicit parentheses a reader had to reason about precedence
rules to verify correctness:

```python
# Before
return (len(clean_msg1) >= _MIN_SUBSTRING_LEN and clean_msg1 in clean_msg2 or
        len(clean_msg2) >= _MIN_SUBSTRING_LEN and clean_msg2 in clean_msg1)

# After
return ((len(clean_msg1) >= _MIN_SUBSTRING_LEN and clean_msg1 in clean_msg2) or
        (len(clean_msg2) >= _MIN_SUBSTRING_LEN and clean_msg2 in clean_msg1))
```

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```
Exit 0 — no syntax or import errors.
