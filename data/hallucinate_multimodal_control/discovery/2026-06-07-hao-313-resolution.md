# HAO-313 Resolution

Date: 2026-06-07
Task: HAO-313
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:1245

## Finding

The codebase scan found a bare `except Exception:` in
`AdvancedFilecoinStorage._find_deals_for_cid` while reading mock Filecoin deal
JSON files. That path silently ignored unreadable files, invalid JSON, and
unexpected object shapes, making mock storage corruption hard to diagnose.

## Fix

Verified that the current `external/ipfs_kit` gitlink,
`7a92c4573f465d1f3692dfb76cf36ff597872ce6`, already contains the focused fix
for the reported source line through parent commit
`aac0f50cbd7f77d181cbb101889eedc8180e34c2`. No additional source edit was
needed in this HAO worktree. The handler now:

1. Builds `deal_path` before the risky I/O operation so failures can be logged.
2. Catches only `OSError`, `UnicodeDecodeError`, and `json.JSONDecodeError`.
3. Logs skipped unreadable or invalid mock deal files.
4. Rejects non-object JSON payloads with a warning instead of calling `.get()`.

Unexpected programming errors are no longer swallowed by this mock deal scan
loop.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
```

Exit code: 0 (pass)
