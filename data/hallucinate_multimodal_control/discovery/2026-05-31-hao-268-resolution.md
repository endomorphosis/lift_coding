# HAO-268 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py:752
Finding kind: swallowed_exception

## Summary

The scanner flagged line 752 (and nearby line 730) for using `except Exception:`
without binding the exception to a variable, which is inconsistent with the rest
of the file where `except Exception as e:` is the consistent pattern.

Both locations are in metrics-update blocks inside `_get_cache()`. When the
Prometheus counter increment (`.inc()`) raises, the exception must NOT propagate
because metrics failures must not disrupt cache read operations. The intent to
swallow-and-log is correct; the issue was that `logger.exception(...)` was called
without explicit exception binding, which, while functionally correct (Python
captures exc_info from the current context), was inconsistent and unclear.

## Fix

Changed both occurrences from:

```python
except Exception:
    logger.exception("Error updating cache <x> metrics")
```

to:

```python
except Exception as e:
    # Metrics update failures must not disrupt cache operations; log and continue
    logger.exception("Error updating cache <x> metrics: %s", e)
```

This matches the `except Exception as e:` pattern used everywhere else in the file
and makes the intentional swallow explicit with a clarifying comment.

## Validation

python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py — PASSED
