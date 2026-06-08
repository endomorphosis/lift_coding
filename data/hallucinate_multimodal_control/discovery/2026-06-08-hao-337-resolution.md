# HAO-337 Resolution

Date: 2026-06-08
Task: HAO-337
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py:845

## Finding

The scanner reported the bare `except Exception:` in `S3Backend.get_metadata()`
when local cached metadata is read before falling back to S3. That handler
silently discarded every cache-read, JSON, and object-shape failure.

## Fix

Advanced `external/ipfs_kit` to the existing fixed merge commit `e4f84906`,
which includes the line-845 fix from `9b686300`. The metadata-cache fallback now
catches only expected local cache read and metadata-shape failures (`OSError`,
`json.JSONDecodeError`, `KeyError`, `AttributeError`, `TypeError`, `ValueError`,
and `OverflowError`) and logs the cache path and error before falling back to
`head_object`. Unexpected runtime exceptions are no longer swallowed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_s3_backend_complete.py
# exit 0
```
