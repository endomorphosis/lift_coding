# HAO-295 Resolution

Date: 2026-06-12
Task: HAO-295
Kind: swallowed_exception fix
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:1015

## Finding

The scan flagged an `except Exception:` path in `_serialize_ipfs_value()` for
the optional `as_dict()` conversion strategy. The serializer intentionally tries
several conversion strategies before falling back to public attributes, but the
conversion failure must be visible so runtime serialization issues are not
silently discarded.

## Fix

- Added a shared `_warn_ipfs_serializer_fallback(...)` helper that logs
  conversion-strategy failures at WARNING with exception traceback context.
- Routed the `as_dict()`, `to_dict()`, and dataclass `asdict()` fallback paths
  through that helper, preserving the intended fallback behavior while making
  the swallowed-exception path explicit and observable.
- Added focused regression coverage for the `as_dict()` failure path to verify
  that the warning is emitted and public-attribute fallback serialization still
  succeeds.

## Validation

```bash
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Result: passed (exit 0).

```bash
python3 -m unittest hallucinate_app.python.hallucinate_app.test.test_control_surface_policy_ipfs_logic.TestControlSurfacePolicyIpfsLogic.test_ipfs_serializer_logs_as_dict_failure_and_uses_public_attrs
```

Result: passed (exit 0).
