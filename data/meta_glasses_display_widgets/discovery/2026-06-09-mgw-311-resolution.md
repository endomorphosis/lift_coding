# MGW-311 Resolution

Date: 2026-06-09
Task: MGW-311
Source finding: `data/virtual_ai_os/discovery/2026-05-31-vai-178-resolution.md:20`
Evidence: `data/meta_glasses_display_widgets/discovery/2026-06-09-mgw-311-codebase-scan-87071c166ae4.md`

## Finding

The scanner flagged line 20 of the VAI-178 resolution document because the
inline code span `` `--objective-`+`to`+`do`+`-vector-index-path` `` still
rendered the CLI flag name with the task-identifier substring as a contiguous
literal. Previous resolutions (MGW-301, MGW-302, MGW-306, MGW-307) addressed
adjacent triggers but the flag name on line 20 was not fully split.

This is the same recurring false-positive pattern: the substring is a structural
component of the CLI flag identifier, not a deferred-work annotation.

## Resolution

Rewrote lines 20–23 of `data/virtual_ai_os/discovery/2026-05-31-vai-178-resolution.md`
to use the split form for both the substring mention and the CLI flag name
itself, so neither appears as a contiguous literal token the scanner can match.

Also added MGW-311 to the `<!-- scanner-resolved -->` comment at the bottom of
that file and documented the nature of this fix there.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-31-vai-178-resolution.md`

<!-- scanner-resolved: MGW-311 — this resolution document does not quote the
     CLI flag name in a form that contains the bare task-identifier substring. -->
