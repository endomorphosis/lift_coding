# VAI-240 Resolution

Date: 2026-06-08
Task: VAI-240 - Review swallowed exception path in enhanced_storacha_storage.py:1037
Source: external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py:1037
Kind: swallowed_exception
Status: fixed

## Finding

The codebase scan fingerprint `065a828223f1` flagged `_mock_get_blob()` because
it used a bare `except` and silently ignored metadata read failures. Corrupt or
unreadable mock metadata would be hidden, making blob records fall back to
default values without any diagnostic signal.

## Fix

Restricted the handler to expected file and JSON parsing failures
(`OSError`, `ValueError`) and log the metadata path plus error. The mock blob
lookup still returns the stored blob with fallback metadata, but the failure is
now visible and unexpected exceptions are no longer swallowed by this block.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/enhanced_storacha_storage.py
```

Result: PASS (exit code 0).
