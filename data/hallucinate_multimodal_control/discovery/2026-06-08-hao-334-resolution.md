# HAO-334 Resolution

Date: 2026-06-08
Task: HAO-334
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_s3_backend.py:236

## Finding

The scanner reported the broad `except Exception as e:` in `_add_to_cache()`.
That handler logged cache write failures and returned `None`, but it also
covered unexpected runtime errors and could leave partially written cache data
or metadata files behind.

## Fix

`_add_to_cache()` now catches only expected cache persistence failures
(`OSError`, `TypeError`, and `ValueError`), logs the traceback, and removes
partial cache artifacts before returning `None`. Cache population remains
best-effort for callers, while unexpected exceptions are no longer swallowed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_s3_backend.py
# exit 0
```
