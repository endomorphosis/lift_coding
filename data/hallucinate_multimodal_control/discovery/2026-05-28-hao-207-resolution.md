# HAO-207 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py:1095
Status: fixed

## Bug

`_messages_similar` used a regex pattern with lowercase-only hex character classes
(`0x[0-9a-f]+` and `ID: [a-f0-9-]+`).  Error messages containing uppercase hex
addresses (e.g. `0xDEADBEEF`) or uppercase UUID segments were not normalised,
causing `_find_duplicate_error` to miss genuine duplicates and log the same error
repeatedly.

## Fix

- Added class-level compiled pattern `ErrorMonitor._SIMILAR_PATTERN` using
  explicit `[0-9a-fA-F]` ranges and `re.IGNORECASE`, so both cases are scrubbed.
- Compiling the pattern once at class definition avoids repeated compilation on
  every `_messages_similar` call.
- Replaced the two inline `re.sub(pattern, ...)` calls with
  `self._SIMILAR_PATTERN.sub('XXX', ...)`.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/error_monitor.py
# exit 0
```
