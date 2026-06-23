# VAI-199 Resolution

Date: 2026-06-23
Task: VAI-199 — Review swallowed exception path in control_surface_policy.py:1032
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py

## Finding

The codebase scan (fingerprint 457c986ab6c2) found `except Exception:` handlers in
`_serialize_ipfs_value()` that were silently swallowing serialization failures. In the
current file layout, VAI-198 has already made the `to_dict()` fallback visible. The
matching VAI-199 path is the dataclass `asdict()` fallback, which still caught every
exception and continued to later fallback serializers without diagnostics.

## Fix Applied

The dataclass `asdict()` fallback now binds the caught exception and logs a warning with
traceback before trying the remaining `__dict__` and `repr()` serializers. The broad
catch remains intentional because `_serialize_ipfs_value()` receives arbitrary upstream
IPFS objects and must continue through its fallback chain, but the failure is no longer
silent.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exit code 0 — syntax valid.
