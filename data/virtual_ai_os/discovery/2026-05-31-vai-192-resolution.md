# VAI-192 Resolution

Date: 2026-06-05
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_manager.py:1029
Kind: swallowed_exception → fixed

## Change

The bare `except Exception: pass` that drained `scale_futures` after the
auto-scaling test was replaced with explicit, logged exception handling
consistent with the timeout-test pattern already present at line 984:

```python
except (TimeoutError, concurrent.futures.TimeoutError):
    logger.debug("Scale test task timed out during cleanup")
except Exception as e:
    logger.debug("Scale test task raised unexpected exception during cleanup: %s", e)
```

Timeout errors are expected here (tasks are intentional `time.sleep` lambdas
that may still be running when we drain). Other exceptions are unexpected but
harmless at this stage; logging them at DEBUG ensures diagnostics are never
silently lost.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/thread_pool_manager.py` → exit 0
