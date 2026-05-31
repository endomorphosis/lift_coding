# VAI-153 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py:752
Kind: swallowed_exception

## Finding

`except Exception as e:` at line 752 (and matching line 730) swallowed metric update
exceptions in `_get_cache`, logging only the string representation without a traceback.
This made it hard to debug prometheus/observability failures in production.

## Fix

- Changed `logger.error(...)` → `logger.warning(..., exc_info=True)` for both cache-hit
  (line 730) and cache-miss (line 752) metrics update exception handlers.
- Added comment clarifying these are intentionally non-fatal (metrics failures must not
  break the main cache lookup path).
- Also fixed two pre-existing syntax errors at lines 2000 and 2015 where malformed
  chained ternary expressions (`x if y if z else w else v`) caused `SyntaxError`;
  replaced with correctly parenthesized ternaries.

## Outcome

`python3 -m py_compile` passes. Swallowed exception now emits a full traceback at
WARNING level, making future debugging straightforward without changing behaviour.
