# HAO-321 Resolution

Date: 2026-06-08
Task: HAO-321
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:981

## Finding

The scan reported a bare `except:` while parsing mock Storacha pagination
cursors in `_mock_list_blobs()`. Invalid cursors were silently reset to the first
page, hiding malformed cursor input and making repeated first-page pagination
hard to diagnose.

## Fix

Replaced the bare handler with explicit `TypeError` and `ValueError` handling.
Malformed cursor values still fall back to the first page to preserve the mock
backend's prior behavior, but the invalid cursor and parse error are now logged
at warning level. Non-conversion exceptions are no longer swallowed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py
# exit 0
```
