# HAO-203 Fix: Swallowed Exception in get_authorized_key_info

Date: 2026-05-28
Task: HAO-203
Kind: swallowed_exception fix
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:288

## Problem

`get_authorized_key_info` caught `Exception` at line 288, logged it, then returned `None`.
This made internal failures indistinguishable from the intentional `None` return for
unauthorized or not-found cases, preventing callers from handling errors correctly.

## Fix

Changed `return None` to `raise` in the except block so unexpected exceptions propagate
to callers. Updated the docstring to document the `Raises` contract.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py
# exit 0
```
