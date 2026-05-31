# VAI-191 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_integration.py:830

## Finding

The codebase scan flagged a bare `except Exception: pass` block at line 830 that
silently swallowed any exception from `history_future.result(timeout=1.0)` in the
integration test method.  The original code was:

```python
# Wait for result
try:
    history_future.result(timeout=1.0)
except Exception:
    pass
```

## Fix Applied

The exception is now captured and surfaced in the test-result report rather than
being silently discarded:

```python
# Wait for result; capture any exception so it can be surfaced in the
# test report rather than being silently swallowed.
history_future_error: str | None = None
try:
    history_future.result(timeout=1.0)
except Exception as e:
    history_future_error = str(e)
```

The error is included in the `task_history` step details dict when present:

```python
**({"future_error": history_future_error} if history_future_error else {})
```

No other behaviour changed.  The fix was landed in submodule commit `d9ba433`.

Validation: `python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_integration.py` exits 0.
