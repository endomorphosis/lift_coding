# HAO-338 Resolution

Date: 2026-06-08
Task: HAO-338
Source: external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:472
Finding: swallowed_exception

## Resolution

The worktree pins `external/ipfs_kit` to commit `dee1ac56178959a618f724ef98c2d61c9ab9f4cc`, which already contains the focused runtime fix for this finding.

At the reported cache-write path, `_add_to_cache` no longer catches every `Exception`. It now handles the expected local cache failure classes `(OSError, TypeError, ValueError)`, writes data and metadata through temporary files before atomically replacing cache entries, cleans up partial cache artifacts on failure, returns `Optional[str]`, and logs the cache-write failure with `exc_info=True`.

## Validation

Result: passed in this worktree.

```sh
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py
```
