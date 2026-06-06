# HAO-294 Resolution

Date: 2026-06-06
Task: HAO-294
Kind: swallowed_exception fix
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:779

## Finding

Two bare `except Exception: pass` clauses in `_ipfs_explanations()` were
silently discarding errors from optional explanation-gathering calls
(`compile_explain_iter` and `NLUCANPolicyCompiler.compile_explain`).  The
function is designed to be fault-tolerant (it tries multiple optional paths),
but completely swallowing exceptions made failures invisible during debugging
and operations.

## Fix

- Added `import warnings` to the module imports.
- Changed both `except Exception: pass` blocks to capture the exception with
  `as exc` and emit a `warnings.warn(...)` message.
- The function still continues gracefully if either optional path fails, but
  callers / developers now see a `UserWarning` surfacing the root cause.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exit code: 0 (pass).
