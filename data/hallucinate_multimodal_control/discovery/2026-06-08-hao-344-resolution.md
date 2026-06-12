# HAO-344 Resolution

Date: 2026-06-08
Task: HAO-344
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/lassie_mock_server.py:59

## Finding

The scan fingerprint `3ea0f0198aff` flagged the bare `except:` in the Lassie
mock server retrieval listing path. Invalid or unreadable retrieval JSON files
were silently dropped, and the broad handler could also swallow unrelated
runtime exceptions.

## Fix

The retrieval listing loop now catches only `OSError` and
`json.JSONDecodeError`, logs the skipped retrieval filename through the request
handler, and leaves unexpected exceptions visible.

## Validation

Result: passed.

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/lassie_mock_server.py
```
