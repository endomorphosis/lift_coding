# HAO-204 Resolution

Date: 2026-05-28
Task: HAO-204
Finding: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:376

## Status: Fixed

The `issue_key_access_capability` method in `AuthKeystoreIntegration` was swallowing all
exceptions from the auth backend, returning `None` and making it impossible for callers to
distinguish between an intentional authorization denial (legitimate `None` return) and a
backend failure.

## Change Made

In the `except Exception as e` block of `issue_key_access_capability` (around line 386),
changed from silently returning `None` to re-raising the exception after logging:

```python
# Before (swallowed exception):
except Exception as e:
    logger.exception(f"Failed to issue key access capability for {provider_id}: {e}")
    return None

# After (propagates unexpected errors):
except Exception as e:
    logger.exception(f"Failed to issue key access capability for {provider_id}: {e}")
    raise
```

The docstring was also updated to document the `Raises` contract:

```
Raises:
    ValueError: If the module has not been initialized.
    Exception: Propagates any unexpected error from the auth backend after logging it.
```

This matches the pattern of the sibling methods `list_authorized_providers` and
`get_authorized_key_info` in the same file which already use `raise`.

Note: `rotate_authorized_key` (a different method in the same file) still returns `False`
on exception — that is intentional as rotation failure is a recoverable condition and is
not in scope for HAO-204.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py` — PASS
