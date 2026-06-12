# HAO-299 Resolution

Date: 2026-06-06
Finding: swallowed_exception
Source: hallucinate_app/python/hallucinate_app/control_surface_store.py:508

## Fix Applied

The swallowed `as_dict()` exception path in `_json_safe()` was updated to bind
the exception and emit a warning via the module-level
`_log = logging.getLogger(__name__)` logger with exception context.

The fallback logic is preserved: if `as_dict()` raises, we still try `to_dict()`,
and if that also raises we fall through to the remaining serialization
strategies. Recursive serialization of a successful `as_dict()` result now
happens outside the hook-failure `try` block, so nested serialization errors are
not mislabeled as hook failures. The change ensures unexpected hook failures are
observable rather than silently discarded.

## Changed Files

- `hallucinate_app/python/hallucinate_app/control_surface_store.py`
  - Added `import logging` and `_log = logging.getLogger(__name__)`
  - Replaced the swallowed `as_dict()` exception with a warning log and fallback

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_store.py
# exit 0 - no syntax errors
```
