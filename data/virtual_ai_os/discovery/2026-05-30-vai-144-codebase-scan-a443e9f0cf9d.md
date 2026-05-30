# VAI-144 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: a443e9f0cf9d9850aedb56a125d3dded6c829021
Kind: annotated_followup
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1114
Priority: P2
Track: runtime

## Evidence

```text
clean_msg1 = self._SIMILAR_PATTERN.sub('XXX', msg1)
```

## Analysis

The sentinel token `'XXX'` used to replace volatile details (addresses, line
numbers, timestamps, IDs) could collide with real error message text. For
example, a test framework or placeholder message that contains the literal
string `XXX` would be incorrectly treated as a normalised volatile token,
potentially causing false-positive similarity matches between unrelated errors.

## Fix Applied

Introduced `ErrorMonitor._SIMILAR_SENTINEL = '\x00'` (null byte) as the
replacement token. A null byte cannot appear in ordinary Python error-message
strings, eliminating the collision risk. The sentinel is 1 character long
(< `_SIMILAR_MIN_LEN = 10`), preserving the existing guard behaviour that
prevents fully-volatile messages from being falsely deduplicated against each
other.

Changed files:
- `hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py`
  - Added `_SIMILAR_SENTINEL = '\x00'` class constant (with doc-comment)
  - Updated `_messages_similar` to use `self._SIMILAR_SENTINEL` instead of `'XXX'`
- `hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`
  - Added `test_message_containing_sentinel_not_falsely_similar` (VAI-144)

All 17 `TestMessagesSimilar` tests pass.

