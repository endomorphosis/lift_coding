# HAO-300 Resolution

Date: 2026-06-07
Task: HAO-300
Kind: swallowed_exception fix
Source: hallucinate_app/python/hallucinate_app/control_surface_store.py:513

## Finding

The original scan evidence flagged the `_json_safe` fallback branch that handled
objects with a `to_dict()` method. A prior remediation made the fallback visible
in debug logs, but the guarded expression still wrapped both `value.to_dict()`
and recursive `_json_safe(...)` conversion. That meant a nested serialization
failure after a successful `to_dict()` call could be mistaken for a bad
`to_dict()` hook and hidden by later fallback strategies.

## Fix

The `to_dict()` call is now isolated inside the `try` block and assigned to a
local `raw` value. Recursive serialization runs in the `else` branch, so
unexpected serialization errors are no longer swallowed by the hook fallback.

Failures raised directly by `to_dict()` remain recoverable because this helper
serializes best-effort policy artifacts. Those failures now log at WARNING level
with traceback information before falling through to the remaining dataclass,
public-attribute, and string fallback strategies. A short `_json_safe` docstring
documents that distinction for future scans.

## Validation

```bash
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_store.py
```

Exit code: 0 (PASS)
