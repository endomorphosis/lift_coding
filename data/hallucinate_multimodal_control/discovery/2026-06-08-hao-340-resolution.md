# HAO-340 Resolution

Date: 2026-06-08
Task: HAO-340
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1549

## Finding

The scan fingerprint `070deff5a913` flagged the broad, silent
`except Exception:` in `StorachaBackend.get_status()` while parsing optional
Storacha status response version metadata. Malformed or unexpected response
JSON hid all failures and left `api_version` unset without any diagnostic
signal.

## Fix

The version metadata parser now catches only JSON decoding failures
(`ValueError`) and logs them with traceback context at debug level. Successfully
decoded responses are checked for the expected object shape before reading the
`version` key; non-object JSON is logged instead of being silently ignored.

## Validation

Result: passed.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py
```
