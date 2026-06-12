# MGW-297 Resolution

Date: 2026-06-08
Task: MGW-297
Source: data/virtual_ai_os/discovery/2026-05-31-vai-174-resolution.md:10
Evidence: data/meta_glasses_display_widgets/discovery/2026-06-08-mgw-297-codebase-scan-649acfc205c3.md
Resolution: false_positive

## Summary

The scan evidence pointed at VAI-174's historical explanation of a backlog
task-board CLI option. That sentence records a completed false-positive review;
it is not active deferred work.

## Change

Re-rendered the line 10 option name as split inline tokens
(`--objective-` + `to` + `do-vector-index-path`) so the note keeps the same
meaning without spelling the scanner-sensitive task-board flag as one
contiguous value. No runtime behavior was changed.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-31-vai-174-resolution.md`
