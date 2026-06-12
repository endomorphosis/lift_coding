# HAO-293 Resolution

Date: 2026-06-06
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_thread_pool_monitor.py:324
Kind: swallowed_exception

## Finding

Bare `except Exception: pass` in cleanup loop at line 324 silently discarded all
exceptions — including unexpected ones that could indicate real bugs in the
thread pool monitor or tasks under test.

## Fix

- Replaced the bare `except Exception: pass` with explicit expected cleanup
  handling for `TimeoutError` and `CancelledError`.
- Unexpected future exceptions are collected while the cleanup loop continues
  through every future, then the test fails with the first unexpected exception.
  This keeps later tests isolated without swallowing real task failures.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_thread_pool_monitor.py
```
Exit code: 0
