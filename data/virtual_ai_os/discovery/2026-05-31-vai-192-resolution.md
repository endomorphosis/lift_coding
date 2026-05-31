# VAI-192 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_manager.py:1029
Kind: swallowed_exception → fixed

## Change

The bare `except Exception: pass` that drained `scale_futures` after the
auto-scaling test was changed to log the exception at DEBUG level:

```python
except Exception as exc:
    logger.debug("Scale-test future raised (expected during drain): %s", exc)
```

Exceptions during this drain are harmless (the tasks are intentional
`time.sleep` lambdas that can also timeout), but logging them ensures
diagnostics are not silently lost if something unexpected occurs.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_manager.py` → exit 0
