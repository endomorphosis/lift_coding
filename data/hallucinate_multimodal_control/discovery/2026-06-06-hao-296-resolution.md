# HAO-296 Resolution

Date: 2026-06-06
Task: HAO-296
Source finding: `hallucinate_app/python/hallucinate_app/control_surface_policy.py:1020`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-06-hao-296-codebase-scan-a71af3b6f995.md`

## Finding

The scanner flagged `except Exception:` clauses in the `_serialize_ipfs_value`
helper (lines 1025, 1030, 1035 after the original scan). Each `try` block
wrapped both the conversion method call (`as_dict()`, `to_dict()`, `asdict()`)
**and** the subsequent recursive `_serialize_ipfs_value(...)` call in a single
exception handler. That meant any exception raised *during recursive
serialization of the converted value* was silently caught, logged only at DEBUG
level, and the code fell through to the next strategy — hiding real bugs in
nested objects.

## Root Cause

```python
# Before (problematic): both as_dict() AND the recursive call were inside try
if hasattr(value, "as_dict"):
    try:
        return _serialize_ipfs_value(value.as_dict())   # ← recursive call swallowed
    except Exception:
        _logger.debug("as_dict() failed ...", exc_info=True)
```

If `as_dict()` succeeded but the result contained a value that raised during
`_serialize_ipfs_value`, that inner exception was swallowed by the outer
`except Exception` and the fallback chain continued silently.

## Fix

Split each `try` block using `try/except/else` so that only the conversion
method call is guarded; the recursive serialization call moves to the `else`
branch and any exception it raises propagates normally:

```python
if hasattr(value, "as_dict"):
    try:
        raw = value.as_dict()
    except Exception:
        _logger.debug("as_dict() failed for %r; trying next strategy", type(value), exc_info=True)
    else:
        return _serialize_ipfs_value(raw)
```

The same pattern was applied to the `to_dict` and `asdict` blocks.

## Validation

```bash
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Result: passed (exit 0).
