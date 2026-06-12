# HAO-343 Resolution

Date: 2026-06-08
Task: HAO-343
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/ipfs_ipns_operations.py:1501

## Finding

The scanner flagged the per-key `except Exception as resolve_e:` in
`IPNSOperations.get_records()`. That handler logged a warning and then
continued, so unexpected exceptions from the resolve path were hidden while
`get_records()` still reported overall success.

## Fix

Removed the per-key broad exception handler. Expected IPFS/API resolution
failures still continue through `resolve()` returning `success: False`, while
unexpected exceptions now reach the existing outer `get_records()` exception
handler, which records failed metrics and returns a failed result with
exception details.

## Validation

Result: passed in this worktree.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/ipfs_ipns_operations.py
```
