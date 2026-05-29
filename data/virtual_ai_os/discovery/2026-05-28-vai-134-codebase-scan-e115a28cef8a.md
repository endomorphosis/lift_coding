# VAI-134 Codebase Scan Finding

Date: 2026-05-28
Fingerprint: e115a28cef8a8a2e9146a65052602d965c9cbf66
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1110
Priority: P2
Track: runtime

## Evidence

```text
clean_msg1 = self._SIMILAR_PATTERN.sub('XXX', msg1)
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (VAI-134, 2026-05-28)

The scan flagged `_SIMILAR_PATTERN.sub('XXX', msg1)` because `msg1` could be
`None` at runtime despite the `str` type annotation.  A prior fix (VAI-131/132)
already added an `isinstance` guard at lines 1101-1106 so `re.sub` is only
called on confirmed `str` values.

Two additional improvements were landed in this task:

1. **Explicit parentheses** around the `and`/`or` clauses of the substring-match
   `return` statement (line 1121) to make operator precedence unambiguous and
   prevent future misreads.

2. **New focused test** `TestMessagesSimilar::test_short_normalised_message_not_substring_matched`
   exercises the `_MIN_SUBSTRING_LEN` guard: a message that normalises to a
   token shorter than 10 characters (`"line 42"` → `"XXX"`) must not be
   considered similar to an unrelated message via substring matching.

All 8 `TestMessagesSimilar` tests pass.  The scan should not re-file this
finding; the root cause (un-guarded `re.sub`) was already addressed and this
task hardened the surrounding code and test coverage.
