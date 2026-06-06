# HAO-299 Resolution

Date: 2026-06-06
Finding: swallowed_exception
Source: hallucinate_app/python/hallucinate_app/control_surface_store.py:508

## Fix Applied

The two `except Exception: pass` blocks in `_json_safe()` (lines 506-514) were
updated to bind the exception and emit a `DEBUG`-level log entry via a
module-level `_log = logging.getLogger(__name__)` logger.

The fallback logic is preserved: if `as_dict()` raises, we still try `to_dict()`,
and if that also raises we fall through to the remaining serialization strategies.
The change ensures that unexpected failures are observable in debug logs rather
than being silently discarded.

## Changed Files

- `hallucinate_app/python/hallucinate_app/control_surface_store.py`
  - Added `import logging` and `_log = logging.getLogger(__name__)`
  - Replaced `except Exception: pass` with `except Exception as exc: _log.debug(...)`

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_store.py
# exit 0 — no syntax errors
```
