# HAO-317 Resolution

Date: 2026-06-07
Task: HAO-317
Source: external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:430

## Finding

The scanner flagged a bare `except:` in the `to_ipfs` temporary-file cleanup
path. That handler swallowed all exceptions raised by `os.unlink`, including
non-cleanup control-flow exceptions.

## Fix

Replaced the bare handler with explicit cleanup handling:

- `FileNotFoundError` is treated as a benign already-removed temp file and
  logged at debug level.
- Other `OSError` cleanup failures are logged at warning level so they remain
  visible without masking the `ipfs add` result.

This keeps cleanup best-effort while avoiding a catch-all exception path.
