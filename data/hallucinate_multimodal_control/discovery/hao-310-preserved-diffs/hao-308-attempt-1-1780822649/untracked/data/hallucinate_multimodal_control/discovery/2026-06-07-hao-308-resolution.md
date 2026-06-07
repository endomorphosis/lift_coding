# HAO-308 Resolution

Date: 2026-06-07
Finding: swallowed_exception
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984

## Fix Applied

The broad `_get_chain_height()` exception handler was removed. Mock Filecoin
network stats are now parsed directly and invalid local state raises a specific
`ValueError` instead of being hidden behind fallback chain height generation.

The helper still returns `None` when no usable live chain head is available, which
preserves the existing synthetic-height fallback for unavailable Lotus/API
responses. Nearby callers now test `is None` so a valid height of `0` is not
treated as missing.

## Validation

```bash
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
```
