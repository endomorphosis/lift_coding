# HAO-313 Resolution

Date: 2026-06-12
Task: HAO-313
Kind: swallowed_exception review
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245

## Finding

The scan evidence reported a swallowed `except Exception:` in
`AdvancedFilecoinStorage._find_deals_for_cid` while reading mock Filecoin deal
JSON files.

## Resolution

The current `external/ipfs_kit` checkout already contains the focused exception
narrowing for this path: the mock deal-file read now catches only `OSError`,
`UnicodeDecodeError`, and `json.JSONDecodeError`, logs the skipped file, and
rejects non-object JSON payloads before calling `.get()`.

This pass kept that behavior and made the file read explicitly UTF-8 encoded so
the existing `UnicodeDecodeError` handling is deterministic across runtime
environments. Unexpected programming errors in the mock deal scan loop are not
swallowed.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
```

Pass.
