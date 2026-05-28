# VAI-126 Resolution

Date: 2026-05-28
Task: VAI-126 — Review swallowed exception path
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:150
Kind: swallowed_exception
Status: fixed

## Root Cause

Seven `except Exception as e:` blocks across `AuthKeystoreIntegration` methods were
logging the exception via `logger.exception(...)` but then returning `None` or `False`
instead of re-raising. This meant callers could not distinguish between an intentional
"unauthorized" result (also `None`/`False`) and an unexpected infrastructure failure.

## Fix

Changed all seven swallowed-exception blocks from `return None`/`return False` to `raise`,
preserving the existing `logger.exception` call for diagnostics while allowing the
exception to propagate to the caller. Methods affected:

- `get_authorized_key` (line 150)
- `set_authorized_key`
- `delete_authorized_key`
- `list_authorized_providers`
- `get_authorized_key_info`
- `rotate_authorized_key`
- `issue_key_access_capability`

Note: `init()` already returned `False` on failure; that method is not a data-access
path so suppressing there is acceptable (callers check the bool return). It was left
unchanged.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py
```

Result: PASS (exit code 0)
