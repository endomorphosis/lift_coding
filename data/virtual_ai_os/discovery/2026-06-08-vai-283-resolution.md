# VAI-283 Resolution

Date: 2026-06-08
Task: VAI-283
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/ipfs_development/ipfs_mcp_tools.py:514

## Finding

The `finally` block in `ipfs_files_write` silently swallowed `OSError` when
deleting a temporary file (`os.unlink(temp_path)`), making it impossible to
detect temp-file leaks in production.

## Fix

Changed `except OSError: pass` to bind the exception and emit a `logger.debug`
message with the temp path and error. This:

- Keeps the cleanup non-fatal (temp-file deletion failure should not abort the
  write result that was already returned).
- Makes failures visible in debug logs so operators can investigate temp-file
  accumulation.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/ipfs_development/ipfs_mcp_tools.py
```

Exits 0 — no syntax errors introduced.
