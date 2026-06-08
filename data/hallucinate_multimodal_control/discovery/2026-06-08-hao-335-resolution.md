# HAO-335 Resolution

Date: 2026-06-08
Task: HAO-335
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_s3_backend.py:698

## Finding

The scanner reported the bare `except Exception:` in `S3Backend.get_metadata()`
when local cached metadata is read before falling back to S3. That handler
silently discarded malformed or unreadable cache metadata errors.

## Fix

Advanced `external/ipfs_kit` to the existing line-698 fix commit `6e90bda`,
which validates that cached metadata is a JSON object, catches only expected
local cache read and shape failures (`OSError`, `TypeError`, `ValueError`), and
logs the fallback to S3 with `exc_info=True`. Cache metadata reads remain
best-effort, while unexpected runtime errors are no longer silently swallowed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_s3_backend.py
# exit 0
```
