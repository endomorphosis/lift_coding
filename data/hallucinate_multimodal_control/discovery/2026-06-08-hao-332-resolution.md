# HAO-332 Resolution

Date: 2026-06-08
Task: HAO-332
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py:59

## Finding

The scanner reported the broad `except Exception as e:` in `backup_file()`.
That helper logged backup failures and returned `None`, while both Lassie update
callers ignored the return value before overwriting the original files.

## Fix

`backup_file()` now catches only filesystem and shutil copy failures
(`OSError` and `shutil.Error`) and re-raises after logging them. Backup failures
therefore abort the enclosing update path instead of allowing the script to keep
modifying files without a valid backup.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py
# exit 0

python3 - <<'PY'
... monkeypatch shutil.copy2 to raise OSError and call backup_file(...)
PY
# exit 0
```
