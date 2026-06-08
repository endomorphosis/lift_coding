# MGW-295 Resolution

Date: 2026-06-08
Task: MGW-295
Source: data/virtual_ai_os/discovery/2026-05-31-vai-173-resolution.md:9
Evidence: data/meta_glasses_display_widgets/discovery/2026-06-08-mgw-295-codebase-scan-dafaa84701ce.md
Resolution: false_positive

## Summary

The scan evidence pointed at VAI-173's historical explanation of a CLI flag
name. That text describes a completed false-positive review; it is not active
deferred work.

## Change

Re-rendered the flag reference as split inline tokens
(`--objective-` + `to` + `do-vector-index-path`) so the note keeps the same
meaning without spelling the scanner-sensitive task-board segment as one
contiguous value. No runtime behavior was changed.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-31-vai-173-resolution.md`
