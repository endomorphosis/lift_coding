# HAO-354 Resolution

Date: 2026-06-08
Task: HAO-354
Finding: swallowed_exception at external/ipfs_kit/archive/archive_clutter/fix_scripts/patch_direct_mcp.py:31

## Analysis

The three `except Exception as e:` blocks in this file all used `logger.exception()` to log
with a full traceback, so exceptions were not silently discarded. However, catching the broad
`Exception` type masks unexpected errors and makes debugging harder.

## Fix Applied

Replaced broad `except Exception as e:` with specific exception types in all three functions:

- `load_tools()` (line 31): `except (OSError, json.JSONDecodeError) as e:`
- `create_patched_mcp_server()` (line 94): `except (OSError, json.JSONDecodeError) as e:`
- `create_restart_script()` (line 128): `except OSError as e:`

Also removed redundant `{e}` from `logger.exception()` format strings since `logger.exception`
already captures and logs the exception representation in the traceback.

## Result

Unexpected exceptions (e.g., `MemoryError`, `SystemExit`) now propagate instead of being
swallowed, while expected IO/JSON errors are handled gracefully with logging and a safe
return value for callers.
