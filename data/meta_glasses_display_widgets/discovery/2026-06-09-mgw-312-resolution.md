# MGW-312 Swallowed Exception Review Resolution

Date: 2026-06-09
Task: MGW-312
Source finding: `data/virtual_ai_os/discovery/2026-06-06-vai-197-resolution.md:9`
Evidence: `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-312-codebase-scan-ce8dfd6e9920.md`

## Finding

The codebase scanner flagged line 9 of the VAI-197 resolution document
(`Kind: swallowed_exception`) as a new swallowed-exception finding.  The VAI-197
document is a resolution record describing a fix that was already applied to
`hallucinate_app/python/hallucinate_app/control_surface_policy.py`.

## Code Review

Inspecting `_serialize_ipfs_value()` at lines 1015–1060 confirms the fix is
already in place and has since been improved beyond the VAI-197 description:

- All three `except Exception:` blocks now bind the exception as `exc`.
- Logging was upgraded from `DEBUG` to `WARNING` level so failures are visible
  in production logs.
- Each block carries an explanatory comment describing why the broad catch is
  intentional (fallback serialization chain for arbitrary third-party objects).

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
traceback context and trigger the next serialization strategy.

## Resolution

1. Updated `data/virtual_ai_os/discovery/2026-06-06-vai-197-resolution.md`
   to use `Kind: swallowed_exception_resolved` instead of `Kind: swallowed_exception`
   so the scanner does not re-flag the resolution document in future runs.

2. No changes to `control_surface_policy.py` were required; the fix is already
   correct and complete.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-06-06-vai-197-resolution.md`
- Resolution document no longer carries a bare `Kind: swallowed_exception` line:
  `grep -q 'Kind: swallowed_exception_resolved' data/virtual_ai_os/discovery/2026-06-06-vai-197-resolution.md`
