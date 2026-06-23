# VAI-197 Resolution

Date: 2026-06-23
Task: VAI-197 - Review swallowed exception path in control_surface_policy.py:1022
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py

## Finding

The codebase scan fingerprint `c7debe50e8cb` reported a swallowed
`except Exception:` path near the IPFS policy evaluator compatibility shim. In
the current file layout, the matching path is the optional import of
`ipfs_datasets_py.mcp_server.temporal_policy.PolicyEvaluator`.

## Fix

The compatibility shim now catches only `ImportError` and records debug
diagnostics before continuing without the optional shim. Non-import failures
from the upstream module are no longer hidden by the shim; they can propagate to
the existing fail-closed evaluator path with a visible failure reason.

## Validation

Run:

```text
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```
