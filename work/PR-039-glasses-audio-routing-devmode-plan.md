# PR-039: Glasses audio routing + devmode bypass (mobile)

## Goal
Make Meta AI Glasses audio I/O integration usable for iteration:
- stable connect/disconnect
- predictable routing for mic + speaker
- a "DEV mode" that bypasses glasses (phone mic/speaker) but keeps the same command pipeline

## Scope
- `mobile/glasses/` + `mobile/src/` integration only
- No backend changes required

## Acceptance criteria
- App can run in two modes:
  - Glasses mode: uses glasses mic + output when connected
  - Dev mode: uses phone mic + speaker, but still exercises the same `/v1/dev/audio` -> `/v1/command` -> `/v1/tts` loop
- On-screen diagnostics show:
  - connection state
  - active audio route
  - last error (if any)

## Notes
- Keep implementation minimal; prefer existing scaffolds in `mobile/glasses/`.
