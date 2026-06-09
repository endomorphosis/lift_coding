# HAO-386 Fix: Swallowed Exception in perf.py load_balancing_middleware

Date: 2026-06-09
Task: HAO-386
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/perf.py:791

## Finding

The codebase scan found a bare `except Exception:` at line 791 in
`load_balancing_middleware`. The exception handler was:

1. Overly broad (`Exception` catches everything including programming errors)
2. Too quiet (`logger.debug` means malformed headers silently disappear in production)

## Fix Applied

- Changed `except Exception` → `except (ValueError, TypeError)` to match what
  `float()` actually raises on bad input.
- Upgraded log level from `debug` to `warning` so malformed `X-Response-Time-MS`
  headers surface in production logs without blocking responses.

The outer `except Exception as e:` at the broader middleware level (line 797)
with `logger.error` was already correct; no change needed there.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/perf.py
```
