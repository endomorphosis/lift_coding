# HAO-271 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_database_sync_manager_integration.py:229
Kind: swallowed_exception

## Fix

Replaced bare `except:` clause in `tearDown` with `except Exception as e` and a
`logger.warning(...)` call so that cleanup errors surface in test logs instead of
being silently dropped.  `BaseException` subclasses such as `KeyboardInterrupt`
and `SystemExit` are now allowed to propagate normally.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_database_sync_manager_integration.py
# exit 0
```
