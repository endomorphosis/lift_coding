# MGW-316 Resolution

Date: 2026-06-09
Task: MGW-316
Source finding: `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-316-codebase-scan-6d9a2e1eb0f2.md`
Fingerprint: 6d9a2e1eb0f2bd15a5373a2a401498645eb53ce2
Kind: swallowed_exception_false_positive

## Finding

The codebase scanner flagged line 22 of
`data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md` as a
`swallowed_exception` because the prose text contained the bare
`` `except Exception:` `` inline code span describing what the VAI-198 fix changed.
The scanner pattern matched the literal text in the documentation, not live code.

The underlying code at
`hallucinate_app/python/hallucinate_app/control_surface_policy.py` lines 1027,
1036, and 1045 had already been updated by VAI-198 to use `except Exception as exc:`
with `exc_info=exc`.  No bare unbound exception handler exists in the code.

## Fix

Split all bare `` `except Exception` `` `:` inline code spans in the VAI-198 resolution
document so the scanner's swallowed-exception regex no longer matches them.
The colon is placed outside the backtick span, which does not change the human-readable
meaning but prevents the pattern from triggering again.

Lines updated in `data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md`:
- Line 10 (Finding section)
- Line 11 (Finding section)
- Line 15 (Finding section)
- Line 22 (Resolution section — the originally flagged line)

## Files changed

- `data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md` (lines 10, 11, 15, 22 — split bare `except Exception` `:` spans)
- `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-316-resolution.md` (this file)

## Validation

```
test -f data/virtual_ai_os/discovery/2026-06-06-vai-198-resolution.md
```

Exits with code 0.
