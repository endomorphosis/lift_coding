# HAO-329 Resolution

Date: 2026-06-08
Task: HAO-329
Kind: stale_scan_resolution
Source: external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py:58

## Finding

The codebase scanner reported a swallowed exception at
`external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py:58`
with evidence from a broad `except Exception as e:` block in `backup_file()`.

## Resolution

The pinned `external/ipfs_kit` submodule commit already contains the focused
runtime fix from commit `fb6824f5` (`VAI-249`). `backup_file()` now converts the
input to a `Path`, copies to a `Path` backup target, catches only
`OSError` and `shutil.Error`, and raises a `RuntimeError` with the original
exception chained. The current line 58 is the `try:` statement, and the handler
is the narrowed `except (OSError, shutil.Error) as e:` block on line 60.

No additional code edit was needed for HAO-329 because the swallowed exception
path has already been removed in the checked-out source.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py
# exit 0
```
