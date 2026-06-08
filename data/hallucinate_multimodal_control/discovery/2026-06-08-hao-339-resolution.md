# HAO-339 Resolution

Date: 2026-06-08
Task: HAO-339
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1070

## Finding

The scanner reported the bare `except Exception:` in
`StorachaBackend.get_metadata()` when local disk cache metadata is read before
falling back to the Storacha API. That handler silently discarded cache-read,
JSON decode, and metadata-shape failures.

## Fix

The disk metadata cache fallback now catches only expected local cache failure
classes (`OSError`, `json.JSONDecodeError`, `AttributeError`, `TypeError`, and
`ValueError`) and logs the cache metadata path, CID, and error before falling
back to the API. Unexpected runtime exceptions are no longer swallowed by this
path.

## Validation

Result: passed in this worktree.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py
```
