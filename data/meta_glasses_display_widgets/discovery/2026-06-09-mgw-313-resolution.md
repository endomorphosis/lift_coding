# MGW-313 Swallowed Exception Review Resolution

Date: 2026-06-09
Task: MGW-313
Source finding: `data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md:21`
Evidence: `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-313-codebase-scan-8b595c711daa.md`

## Finding

The codebase scanner flagged line 21 of the VAI-198 resolution document
(`Kind: swallowed_exception`) as a new swallowed-exception finding.  Line 21
reads:

```
- Changed all three `except Exception:` clauses to `except Exception as exc:`
```

This is documentation text *describing* a fix that was previously applied — not
live Python code with a bare `except Exception:`.  The scanner matched the
literal pattern `except Exception:` inside the markdown prose.

## Code Review

Inspecting `_serialize_ipfs_value()` in
`hallucinate_app/python/hallucinate_app/control_surface_policy.py` at lines
1020–1060 confirms the VAI-198 fix is fully in place:

- All three `except Exception as exc:` blocks bind the exception explicitly.
- Each logger call passes `exc_info=exc` (not `exc_info=True`) so the
  traceback is unambiguously tied to the caught exception object.
- Each block carries a comment explaining why the broad catch is intentional
  (fallback serialization chain for arbitrary third-party objects).

Example — current code state:

```python
try:
    raw = value.as_dict()
except Exception as exc:
    # Log at WARNING so failures are visible in production logs rather than
    # silently swallowed.  The fallback chain continues to the next strategy.
    _logger.warning("as_dict() failed for %r; trying next strategy", type(value), exc_info=exc)
else:
    return _serialize_ipfs_value(raw)
```

No exceptions are silently discarded; all failures are logged with full
traceback context and the fallback chain continues to the next serialization
strategy.

## Resolution

1. Added `Kind: swallowed_exception_resolved` to
   `data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md` so the
   scanner does not re-flag the resolution document in future runs.

2. No changes to `control_surface_policy.py` were required; the VAI-198 fix
   is already correct and complete.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md`
