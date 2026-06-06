# HAO-291 Resolution

Date: 2026-06-05
Task: HAO-291
Kind: swallowed_exception
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:768

## Finding

`_ipfs_explanations` contained two `except Exception as exc:` blocks that issued a
`warnings.warn` with the exception message but discarded the full traceback.
Callers could see the warning text but had no stack information for debugging
production failures in the optional IPFS logic adapter path.

## Fix Applied

Added `_logger.debug("...", exc_info=True)` immediately after each `warnings.warn`
call in the two except blocks:

1. After the `compile_explain_iter` fallback (original scan line ~768).
2. After the `NLUCANPolicyCompiler.compile_explain` fallback.

This preserves the full traceback in debug-level logs while keeping the
user-visible `warnings.warn` for non-fatal degradation. No exception is
re-raised because these code paths are intentional fallbacks — the function
still returns whatever explanations were collected from other sources.

## Validation

```
python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py
```

Exit code: 0 (PASS)
