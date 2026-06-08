# HAO-348 Resolution

Date: 2026-06-08
Task: HAO-348
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server.py:251

## Finding

The scan fingerprint `0991e13de35f` flagged the broad
`except Exception as e:` handler in `get_other_instance_pid()`. On the scanned
base, unreadable PID files and invalid PID contents were caught together and the
function returned `None`, hiding the difference between expected missing files
and malformed deployment state.

## Fix

The current submodule source already contains the narrowed runtime path from
commit `e710422a`: missing peer PID files return `None`, `OSError` is logged
with traceback context, invalid or non-positive PID contents are logged as
warnings, and unexpected exceptions are no longer swallowed by this function.

## Validation

Result: passed in this worktree.

```text
python3 -m py_compile external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server.py
```
