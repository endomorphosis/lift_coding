# VAI-195 Resolution

Date: 2026-06-06
Task: VAI-195
Kind: swallowed_exception fix
Source: hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py:1001

## Finding

Bare `except:` clause at line 1001 swallowed all exceptions (including
`KeyboardInterrupt` and `SystemExit`) in the optional psutil resource-collection
block of the `test()` method.

## Fix

Changed:
```python
except:
    pass
```

To:
```python
except Exception as e:
    logger.debug(f"Resource info unavailable (psutil may not be installed): {e}")
    test_results["resources"] = {"available": False, "error": str(e)}
```

This:
1. Restricts the catch to `Exception` subclasses only, letting signals and
   system-exit exceptions propagate correctly.
2. Logs the failure at DEBUG level so operators can diagnose missing psutil.
3. Records the unavailability in `test_results` so callers can inspect it.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py
```
Exit code: 0 (OK)
