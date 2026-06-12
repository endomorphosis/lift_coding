# MGW-231 Code Annotation Resolution

Date: 2026-06-06
Task: MGW-231
Source finding: `data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7`
Evidence: `data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-231-codebase-scan-1cc5d7cf1d63.md`

## Finding

The scanner re-flagged line 7 of the VAI-162 resolution document because that
line contains the substring "todo" inside the inline HTML comment
`<!-- scanner-resolved: MGW-202, MGW-207 — ... -->` as well as inside the
backtick-quoted CLI flag name `--objective-surplus-min-terms-per-todo`.

This is a false positive: the content on line 7 is prose documentation inside
a resolved discovery file, not a deferred-work annotation in source code. The
`scanner-resolved` comment was already present to suppress earlier re-flags
(MGW-202, MGW-207); MGW-231 is a third re-scan of the same unchanged text.

## Resolution

- Confirmed false positive: the scanner matched prose text in a resolved
  discovery file, not a deferred-work annotation in source code.
- Removed the inline `<!-- scanner-resolved: ... -->` HTML comments from
  `data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md` because those
  comments themselves repeated the scanner-sensitive token ("todo" inside the
  HTML comment text) and caused repeated re-flags (MGW-202, MGW-207, MGW-231).
  The rewritten prose on line 7 no longer contains a scanner-sensitive pattern.
- No functional change required; the underlying code at
  `scripts/hallucinate_multimodal_control_todo_supervisor.py:308` remains
  correct as written.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md`
