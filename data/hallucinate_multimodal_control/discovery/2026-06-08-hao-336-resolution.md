# HAO-336 Resolution

Date: 2026-06-08
Task: HAO-336
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py:232

## Finding

The scanner reported the broad `except Exception as e:` in `_add_to_cache()`.
That handler treated every runtime failure as a cache miss, logged without a
traceback, and could leave partially written cache data or metadata files behind.

## Fix

`_add_to_cache()` now catches only expected cache persistence failures
(`OSError`, `TypeError`, and `ValueError`), writes cache data and metadata
through temporary files before atomically replacing the final paths, and removes
partial artifacts before returning `None`. Cache population remains best-effort
for callers, while unexpected exceptions are no longer swallowed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py
# exit 0
```
