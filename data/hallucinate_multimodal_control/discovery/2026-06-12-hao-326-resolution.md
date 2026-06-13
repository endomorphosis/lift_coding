# HAO-326 Resolution

Date: 2026-06-12
Task: HAO-326
Kind: swallowed_exception fix verification
Source: external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:55

## Finding

The scanner reported a swallowed `except Exception as e:` in the backup helper
used before overwriting Storacha integration files. In the original path, a
failed backup was logged but the caller could still continue with the file
mutation, which risked losing the pre-patch source file.

## Resolution

Verified that the current `external/ipfs_kit` gitlink,
`58873ab257104981aa9ba7bee0c2368369716be7`, includes the focused source fix
from `ffa4856aa237f61e0e8dab44875e2a4b29249df3`. The `backup_file` helper now
catches only `OSError` and `shutil.Error`, logs the failure with traceback via
`logger.exception`, and returns `None`. The `update_storacha_kit` caller checks
for that `None` result and aborts before replacing `storacha_kit.py`.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_all_storacha.py
```
