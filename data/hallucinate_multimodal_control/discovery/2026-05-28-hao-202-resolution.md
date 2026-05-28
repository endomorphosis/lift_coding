# HAO-202 Resolution

Date: 2026-05-28
Status: fixed

## Summary

Fixed swallowed exception in `list_authorized_providers` at
`hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:254`.

The except block was returning `None` on any runtime error, making it impossible
for callers to distinguish an authorization denial (expected `None`) from a backend
failure (also `None`). The bug allowed silent data loss when the keystore or auth
service failed.

## Fix

Changed `return None` to `raise` in the except block so unexpected errors propagate
to callers after being logged. `None` is now only returned on a genuine authorization
denial. The docstring was updated with a `Raises` clause.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py` — exit 0
