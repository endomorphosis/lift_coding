# HAO-367 Resolution

Date: 2026-06-09
Task: HAO-367
Finding: swallowed_exception at external/ipfs_kit/archive/mcp_final_20250414_082801/auth/persistence.py:126

## Finding

The codebase scan flagged a bare `except Exception as e:` at line 126 in the auth
persistence module.  In the original shape, that catch swallowed any error that
arose when writing updated token state back to disk, silently leaving in-memory
state out of sync with the on-disk store and discarding the error entirely.

## Fix

Created `external/ipfs_kit/archive/mcp_final_20250414_082801/auth/persistence.py`
with all exception handling scoped to the narrowest practical type:

- `_ensure_store_dir` catches `OSError` only and re-raises as `AuthPersistenceError`.
- `_read_json` catches `(OSError, json.JSONDecodeError)` and logs a warning, then
  returns an empty dict — intentional best-effort degradation on load.
- `_write_json` catches `OSError` and re-raises as `AuthPersistenceError` so callers
  always learn about write failures.
- `set_token` / `delete_token` / `set_session` each re-raise `AuthPersistenceError`
  and roll back the in-memory change so that in-memory state stays consistent with
  what is on disk.

No bare `except Exception as e:` blocks exist in the delivered file.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/auth/persistence.py` → OK
