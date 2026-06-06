# VAI-199 Resolution

Date: 2026-06-06
Task: VAI-199 — Review swallowed exception path in control_surface_policy.py:1032
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py

## Finding

The codebase scan (fingerprint 457c986ab6c2) found `except Exception:` handlers in
`_serialize_ipfs_value()` that were silently swallowing serialization failures.  Prior
tasks HAO-295 through HAO-297 addressed the `as_dict()` and earlier handlers.  VAI-199
addressed the remaining `to_dict()` and `asdict()` handlers (originally at line ~1032,
shifted by prior fixes) which still logged only at DEBUG level.

## Fix Applied

Upgraded both remaining exception handlers from `_logger.debug(...)` to
`_logger.warning(..., exc_info=True)` with an explanatory comment, consistent with the
pattern established for `as_dict()` by HAO-297.  Swallowing the exception is intentional
in this fallback chain — the function tries multiple serialization strategies in sequence
— but failures must be visible in production logs.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exit code 0 — syntax valid.
