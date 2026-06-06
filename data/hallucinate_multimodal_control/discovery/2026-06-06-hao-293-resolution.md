# HAO-293 Resolution

Date: 2026-06-06
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_thread_pool_monitor.py:324
Kind: swallowed_exception

## Finding

Bare `except Exception: pass` in cleanup loop at line 324 silently discarded all
exceptions — including unexpected ones that could indicate real bugs in the
thread pool monitor or tasks under test.

## Fix

- Added `import logging` and imported `TimeoutError as FutureTimeoutError` and
  `CancelledError` from `concurrent.futures`.
- Replaced the bare `except Exception: pass` with two clauses:
  1. `except (FutureTimeoutError, CancelledError): pass` — expected cleanup
     conditions, silently ignored as before.
  2. `except Exception: logging.getLogger(__name__).debug(...)` — unexpected
     exceptions are now logged at DEBUG level (with `exc_info=True`) so they
     appear in test output when `-v` / debug logging is enabled, without
     failing the cleanup loop or the test.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_thread_pool_monitor.py
```
Exit code: 0
