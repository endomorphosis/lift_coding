# HAO-291 Fix: Swallowed Exception Path in control_surface_policy.py:768

Date: 2026-06-09
Task: HAO-291
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py (originally line 768)

## Finding

The `_ipfs_explanations` function caught `Exception` in two places using only
`warnings.warn()`, which meant failures were invisible to structured logging and
production log aggregation.  The exception objects themselves were included in the
warning message but no traceback was recorded.

## Fix Applied

Replaced both `warnings.warn(...)` calls with `_logger.warning(..., exc_info=exc)`
to match the established pattern used elsewhere in the same file (lines 1027–1048).
This ensures:

- Full tracebacks are captured in production logs.
- Failures are surfaced at WARNING level rather than silently swallowed.
- Explanation generation remains best-effort (exceptions are not re-raised).

## Validation

`python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py`
exits 0.

## Not a False Positive

The two bare `except Exception as exc:` / `warnings.warn()` blocks were genuine
maintenance risks: if `compile_explain_iter` or `NLUCANPolicyCompiler.compile_explain`
raised an unexpected error in production the only signal would be a Python warning,
which may be suppressed by the default warnings filter.  The `_logger` path
guarantees the error reaches whatever log handler is configured.
