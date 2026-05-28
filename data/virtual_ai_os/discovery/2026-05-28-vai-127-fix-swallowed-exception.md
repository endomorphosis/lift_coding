# VAI-127 Fix: Swallowed Exception in issue_key_access_capability

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py:376
Kind: swallowed_exception → fixed

## Problem

`issue_key_access_capability` caught all exceptions with `except Exception as e:`,
logged them via `logger.exception(...)`, and then returned `None`. This meant callers
could not distinguish between two distinct outcomes:
- `None` from authorization denial (expected business logic)
- `None` from an unexpected system error (swallowed exception)

## Fix

Changed the exception handler at the former line 376 to **re-raise** after logging:

```python
# Before
except Exception as e:
    logger.exception(f"Failed to issue key access capability for {provider_id}: {e}")
    return None

# After
except Exception as e:
    logger.exception(f"Failed to issue key access capability for {provider_id}: {e}")
    raise
```

The only caller inside the module (`test()`, line ~512) wraps the call in its own
`except Exception as e:` block, so an unexpected error causes the test to report
failure correctly rather than silently claiming a `None` result is equivalent to
"no capability issued".

Updated the method docstring to document the `Raises` behaviour.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/auth_keystore_integration.py` → PASS
