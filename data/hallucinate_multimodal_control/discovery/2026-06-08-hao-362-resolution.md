# HAO-362 Resolution

Date: 2026-06-08
Source: external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:109

## Finding
Bare `except Exception as e:` at line 109 in `kill_existing_servers()` silently
swallowed all errors when killing a pgrep-found process at debug log level,
hiding `PermissionError`, `ValueError`, and other actionable failures.

## Fix
Replaced the single broad handler with specific exception branches:
- `ValueError`: warn and `continue` when pgrep emits non-integer output (pulled out before the kill block)
- `ProcessLookupError`: debug-log only (process already gone, expected)
- `PermissionError`: warn (operator should know they lack permission)
- `OSError`: warn (catch-all for remaining OS-level errors)

Inner `OSError` on the follow-up SIGKILL probe replaced with `ProcessLookupError`
for accuracy (process exited between SIGTERM and the existence check).

## Validation
`python3 -m py_compile external/ipfs_kit/archive/mcp_development/mcp_test_suite.py` passed.
