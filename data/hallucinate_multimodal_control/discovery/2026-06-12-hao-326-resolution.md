# HAO-326 Resolution

Date: 2026-06-12
Task: HAO-326
Source: external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:55

## Review

The scan evidence pointed at a broad backup failure handler:

```text
except Exception as e:
```

In the checked-out `external/ipfs_kit` submodule revision, this path has already
been corrected by commit `ffa4856a` (`VAI-244: Review swallowed exception path in
external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:55`).

The current implementation now catches only backup-related failures:

```python
except (OSError, shutil.Error):
    logger.exception(f"Failed to back up {file_path}")
    return None
```

Callers that require a backup check the `None` return and abort before mutating
the target file. This keeps the archived patch script's boolean-return contract
while preserving exception traceback details in logs, so the original swallowed
exception finding no longer applies to the current target file.

## Validation

Run:

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_all_storacha.py
```
