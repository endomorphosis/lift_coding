# VAI-197 Resolution

Date: 2026-06-06
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:1022
Kind: swallowed_exception_resolved

## Finding

Three `except Exception:` blocks in `_serialize_ipfs_value()` at lines 1022–1044
used bare exception catches without binding the exception to a variable.  Although
`exc_info=True` was already passed to the logger (which captures the current
exception via `sys.exc_info()`), the pattern is clearer and less prone to
future regressions when the caught exception is explicitly bound.

## Fix

Changed all three occurrences from:

```python
except Exception:
    _logger.debug("...", exc_info=True)
```

to:

```python
except Exception as exc:
    _logger.debug("...", exc_info=exc)
```

This is intentional broad catching: `_serialize_ipfs_value` is a serialization
fallback chain for arbitrary third-party objects.  We cannot predict what
exceptions arbitrary `as_dict()`, `to_dict()`, or `dataclasses.asdict()` calls
may raise, so `Exception` is the appropriate scope.  The exceptions are logged
at DEBUG level with full traceback info and are not truly swallowed — they
trigger the next fallback strategy rather than propagating, which is the intended
behaviour.
