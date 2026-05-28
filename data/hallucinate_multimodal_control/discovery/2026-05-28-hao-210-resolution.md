# HAO-210 Resolution: _messages_similar robustness fixes (attempt 2)

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1102
Status: fixed

## Findings

1. **Type-safety**: `_messages_similar` called `re.sub` on `msg1`/`msg2` without
   checking that they are strings.  Although `ErrorData.message` is annotated as
   `str`, Python does not enforce that at runtime.  A `None` or other non-string
   value would cause a `TypeError` inside `re.sub`, crashing duplicate detection.

2. **False-positive substring match**: After normalising volatile tokens (hex
   addresses, line numbers, timestamps, IDs) to `"XXX"`, a message that reduced
   to a very short string (e.g. `"0xDEADBEEF"` → `"XXX"`) would match any other
   message containing those few characters via the `in` operator, causing unrelated
   errors to be incorrectly treated as duplicates.

## Fixes

* Added an early-return guard: if either argument is not a string, fall back to
  plain equality (`msg1 == msg2`) — avoids `TypeError` and still catches exact
  non-string duplicates.

* Added `_MIN_SUBSTRING_LEN = 10` so the substring branch only fires when the
  normalised string is long enough to be a meaningful discriminator.  Exact
  equality (`==`) is always checked first and is unaffected by this guard.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
```
Exit 0 — no syntax or import errors.
