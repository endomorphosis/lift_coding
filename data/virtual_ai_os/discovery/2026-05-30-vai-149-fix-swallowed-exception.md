# VAI-149 Fix: Swallowed Exception in ipfs_kit_server.py

Date: 2026-05-30
Task: VAI-149
File: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_kit_server.py
Line: 329 (original)

## Finding

A bare `except Exception: pass` silently swallowed any file-read errors in
`_mock_add`, making failures invisible and harder to debug.

## Fix

Changed to `except Exception as e: logger.warning(...)` so the error is
surfaced in the log (using the module-level `logger` already present) while
still allowing the mock to continue and return a synthetic CID.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_kit_server.py
# exit 0 ✓
```
