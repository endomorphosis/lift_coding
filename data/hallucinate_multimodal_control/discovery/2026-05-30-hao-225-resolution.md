# HAO-225 Resolution

Date: 2026-05-30
Task: HAO-225
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1115
Kind: false_positive → already_resolved

## Finding

The codebase scan recorded evidence:

```python
clean_msg2 = self._SIMILAR_PATTERN.sub('XXX', msg2)
```

The concern was that the literal string `'XXX'` was used as a sentinel when
normalising volatile details in error messages.  If a real error message contained
the text `XXX`, the normalised form could produce a false-positive similarity match,
silently dropping a distinct error as a duplicate.

## Resolution

This finding is a **false positive against the current code**.  The fix was already
landed by HAO-221 (and related tasks in the same series).  As of that commit:

1. The hardcoded `'XXX'` sentinel was replaced with
   `_SIMILAR_SENTINEL = '\x00'` (a null byte), which cannot appear in real
   error-message strings and therefore cannot produce false-positive matches.
2. A non-string guard was added at line 1114-1115 so that `None` or other
   non-string values passed as `msg1`/`msg2` fall back to equality comparison
   rather than crashing `re.sub` with a `TypeError`.
3. A raw-message identity short-circuit (`if msg1 == msg2: return True`) fires
   before normalisation, ensuring identical messages are always considered
   similar regardless of cleaned length.
4. The `_SIMILAR_MIN_LEN` guard is applied to both the exact-match and
   substring-match paths, preventing two different fully-volatile messages
   (e.g. `"0xdeadbeef"` and `"0xcafebabe"`) from being incorrectly conflated.

The scan evidence captured a snapshot of an earlier version of the file;
line 1115 in the current tree contains `return msg1 == msg2` (part of the
non-string guard), which is correct behaviour.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```

Passes with exit code 0.  No source changes were required for this task.
