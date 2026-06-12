# HAO-356 Resolution

Date: 2026-06-08
Task: HAO-356
Kind: swallowed_exception
Source: external/ipfs_kit/archive/backup_patches/fix_storage_backends.py:288

## Finding

The `update_mcp_server_with_proxies()` function used a bare `except Exception as e`
block at line 288.  The function performs file I/O only (open for read, string
manipulation, open for write), so the only expected exceptions are `OSError` /
`IOError`.  Catching the broader `Exception` silently swallowed programming errors
such as `AttributeError` or `NameError`, hiding bugs from the caller.

## Fix

Narrowed the catch clause from `except Exception` to `except (OSError, IOError)`.
Unexpected exceptions now propagate naturally instead of being returned as `None`.
The log call (`logger.exception`) and the `return None` sentinel were retained
because the caller at line 468 already handles the `None` case gracefully.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/backup_patches/fix_storage_backends.py
# → exit 0 (COMPILE OK)
```

## Changed Files

- `external/ipfs_kit/archive/backup_patches/fix_storage_backends.py` — line 288
