# HAO-289 Resolution: Swallowed Exception at Line 409

Date: 2026-06-09
Task: HAO-289
Source: hallucinate_app/python/hallucinate_app/control_surface_policy.py:409

## Finding

The codebase scan flagged a broad `except Exception:` clause near line 409 of
`control_surface_policy.py`. At the time of the scan (2026-05-31) the file
contained bare `except Exception:` blocks that silently swallowed runtime
failures, making them invisible in production logs.

Related task HAO-290 (completed 2026-06-05) already narrowed the import-guard
clause in `_resolve_ipfs_logic_api` from `except Exception:` to
`except ImportError:`. After that fix the remaining swallowed-exception risk was
in two non-import paths:

1. **`evaluate_ipfs_nl_policy` (line 380 in current file)** — caught
   `Exception as exc` from the upstream `evaluate_nl_policy` call and silently
   returned a deny dict. The exception message appeared in the returned
   `"reason"` key but was never emitted to the Python logging subsystem, making
   it invisible in structured log pipelines and during debugging.

2. **`_compile_ipfs_logic_policy_result` (line 513 in current file)** — caught
   `Exception as exc` from `_call_compile_nl_to_policy` and silently returned a
   clarification result. Same observability gap.

## Fix

Added `_logger.warning(..., exc_info=exc)` immediately before the return
statement in each of the two exception branches, following the established
pattern already used in `_serialize_ipfs_value` (lines 1027–1048). This ensures:

- The full exception traceback is emitted to Python's `logging` subsystem at
  WARNING level whenever either upstream call fails.
- The caller-visible behaviour (deny / clarification result) is unchanged.
- No exceptions are silently swallowed.

## Status

- Validation: `python3 -m py_compile hallucinate_app/python/hallucinate_app/control_surface_policy.py` passes.
- False positive: No; exceptions that are caught but never logged are a genuine
  maintenance and observability risk in production.
