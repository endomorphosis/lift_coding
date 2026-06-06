# HAO-287 Resolution

Date: 2026-06-05
Task: HAO-287
Kind: swallowed_exception fix
Source: hallucinate_app/hallucinate_app/python/ucan_auth_py/ucan_auth_py/crypto/did.py:51

## Finding

The `resolve_did_key` function wrapped its entire body in a broad `except Exception as e` block
that printed the error and returned `None`, silently discarding any unexpected exception. A nested
inner `except Exception` block around `bytes.fromhex` had the same problem.

## Changes Made

File: `hallucinate_app/hallucinate_app/python/ucan_auth_py/ucan_auth_py/crypto/did.py`

1. **Removed outer swallowed exception**: Replaced the outer `try/except Exception` with an
   explicit `isinstance` guard that raises `TypeError` when the caller passes a non-string `did`.
   Unexpected errors now propagate naturally instead of being silenced.

2. **Narrowed inner exception**: Changed `except Exception` → `except ValueError`, which is the
   only exception `bytes.fromhex` raises for invalid hex input.

3. **Replaced `print` with `logging`**: Library code should not write to stdout. Added a
   module-level `logger = logging.getLogger(__name__)` and changed debug messages to
   `logger.debug(...)`.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/ucan_auth_py/ucan_auth_py/crypto/did.py
```
Exit code: 0 (pass)
