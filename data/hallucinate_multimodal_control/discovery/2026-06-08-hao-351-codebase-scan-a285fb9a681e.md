# HAO-351 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: a285fb9a681eda8b7f2846864058607bb053c35c
Kind: swallowed_exception
Source: external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server_with_tools.py:243
Priority: P1
Track: runtime

## Evidence

```text
except Exception as e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (HAO-351)

Status: Fixed

The `except Exception as e:` at line 243 in `start_other_instance()` was overly broad.
`subprocess.Popen` raises `OSError` (executable not found, permission denied) or
`ValueError` (invalid arguments). Catching bare `Exception` silently absorbed any
unexpected errors (e.g., `KeyboardInterrupt` subclasses, memory errors, etc.).

Fix: narrowed the catch to `(OSError, ValueError)` so only the expected failure modes
are handled gracefully, while anything unexpected propagates up the call stack.

Validation: `python3 -m py_compile external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_mcp_server_with_tools.py` → OK
