# VAI-253 Resolution

Date: 2026-06-08
Task: VAI-253 - Review swallowed exception path in fix_lassie_integration.py:273
Source: external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py:273
Kind: swallowed_exception
Status: fixed

## Finding

The codebase scan fingerprint `9451e9cbd0ad` flagged the MCP server restart
helper because its `pkill` fallback caught every `Exception` and ignored the
failure. If the archived patch script were rerun on a host where `pkill` could
not be launched, the cleanup problem would be hidden while the restart continued
with stale process state.

## Fix

Changed the fallback cleanup path to catch only `OSError`, which covers expected
process launch failures such as a missing executable or permission error. The
restart remains best-effort, but the failure is now logged with traceback context
instead of being swallowed.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py
```

Result: PASS (exit code 0).
