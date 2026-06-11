# HAO-371 Resolution

Date: 2026-06-09
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller.py:1119
Kind: swallowed_exception → fixed

## Finding

Bare `except Exception: pass` at line 1119 silently swallowed any error during
JSON content-type detection. This made it impossible to distinguish between
"data is not JSON" and unexpected exceptions (e.g., MemoryError, KeyboardInterrupt
ancestors passed through BaseException, or bugs in the json module call).

## Fix

Replaced `except Exception: pass` with `except (ValueError, UnicodeDecodeError):`
plus a `logger.debug(...)` message so that:

1. Only the expected failure modes (invalid JSON → `ValueError`, bad encoding →
   `UnicodeDecodeError`) are caught silently.
2. A debug-level log entry is emitted so operators can observe the fallback when
   troubleshooting content-type mismatches.
3. Truly unexpected exceptions propagate up to the outer `except Exception as e`
   handler at the function level, which already returns a proper 500 response.

## Status

Fixed. Validation: `python3 -m py_compile` passes.
