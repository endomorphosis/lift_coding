# HAO-297 Codebase Scan Finding

Date: 2026-06-06
Fingerprint: 702ac0beaa18d17641751c9e969e28a3d5d5a1f2
Kind: swallowed_exception
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:1025
Priority: P1
Track: runtime

## Evidence

```text
except Exception:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (HAO-297)

**Not a false positive — maintenance risk / runtime observability bug.**

`_serialize_ipfs_value` uses a deliberate fallback serialization chain
(`as_dict()` → `to_dict()` → `asdict()` → `__dict__` → `repr()`).  Catching
`Exception` broadly is intentional so that arbitrary user-defined objects do not
crash serialization.  However, the original `_logger.debug(...)` call meant that
every failure was invisible unless debug logging was explicitly enabled, making
the exception effectively swallowed in production.

**Fix applied**: changed `_logger.debug` → `_logger.warning` in the `as_dict()`
except block (line 1027) so failures surface in production logs without altering
control flow.  The `exc_info=True` argument is preserved so the full traceback is
always attached to the warning.
