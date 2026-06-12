# HAO-298 Resolution

Date: 2026-06-12
Task: HAO-298
Kind: swallowed_exception fix
Source: hallucinate_app/python/hallucinate_app/control_surface_receipts.py:566

## Finding

The original scan flagged the `_json_safe` branch that handled objects with an
`as_dict()` method. The fallback logged failures at debug level, but the `try`
block wrapped both `value.as_dict()` and recursive `_json_safe(...)`
serialization. A successful `as_dict()` result with a later serialization error
could therefore be treated as an `as_dict()` hook failure and hidden by the
string fallback.

## Fix

The `as_dict()` call is now isolated inside the `try` block and assigned to a
local `raw` value. Recursive serialization runs in the `else` branch, so
unexpected serialization errors are not swallowed by the outer hook fallback.

Failures raised directly by `as_dict()` remain recoverable for best-effort
receipt serialization, but they now log at warning level with traceback
information before falling through to the remaining fallback strategy. A short
`_json_safe` docstring records the intended behavior.

## Validation

```bash
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_receipts.py
PYTHONPATH=hallucinate_app/python python3 -m unittest hallucinate_app.test.test_control_surface_receipts.TestControlSurfaceReceiptJsonSafe
```

Exit code: 0 (PASS)
