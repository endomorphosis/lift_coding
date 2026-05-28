# VAI-131 Codebase Scan Finding

Date: 2026-05-28
Fingerprint: d54c9e83a2ed2b1cbc8c5da8a472ca368ed6b305
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1102
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

## Resolution (VAI-131)

Status: resolved — missing test coverage, not a code bug.

The annotated line `clean_msg1 = self._SIMILAR_PATTERN.sub('XXX', msg1)` is correct.
`ErrorMonitor._SIMILAR_PATTERN` is compiled with `re.IGNORECASE` (line 785) so both
`0xdeadbeef` and `0xDEADBEEF` are normalised to the same `XXX` token, preventing
missed duplicates in `_find_duplicate_error`.

The annotation comment added at lines 1100-1101 correctly describes the behaviour.

A focused `TestMessagesSimilar` test class was added to
`hallucinate_app/test/test_error_monitor.py` to validate:
- Upper- and lower-case hex addresses normalised identically (core IGNORECASE guard)
- Line-number differences normalised
- Date differences normalised
- Truly distinct messages remain distinct

All 5 new assertions pass under `pytest`.
