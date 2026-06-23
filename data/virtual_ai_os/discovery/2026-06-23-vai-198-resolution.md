# VAI-198 Resolution

Date: 2026-06-23
Task: VAI-198 - Review swallowed exception path in control_surface_policy.py:1027
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py

## Finding

The codebase scan fingerprint `e8f8f357776a` reported a swallowed
`except Exception:` path near the IPFS serialization fallback chain.  In the
current file layout, the matching VAI-198 path is the `_serialize_ipfs_value()`
`to_dict()` serializer branch.  It caught every exception and silently continued
to later fallbacks, which made third-party object serialization failures
invisible during runtime debugging.

## Fix

The `to_dict()` branch now binds the exception and logs a warning with traceback
before trying the remaining fallback serializers.  The broad catch remains
intentional because this helper receives arbitrary upstream IPFS objects, but
the failure is no longer swallowed silently.

## Validation

Run:

```text
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```
