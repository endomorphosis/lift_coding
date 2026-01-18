# PR-063: iOS + Ray-Ban Meta MVP1 runbook

## Goal
Create a single, reliable, end-to-end runbook for the MVP1 demo on iOS with Ray-Ban Meta glasses:
- input: phone mic (reliable default)
- output: audio routed to Ray-Ban Meta via iOS bluetooth route
- flow: send command -> get spoken response -> (optional) notifications deep-link

## Why
The backend is mostly in place, but demo success depends on predictable device routing and a repeatable operator checklist.

## Scope
Docs only.

## Deliverables
- New runbook doc under `docs/` with:
  - prerequisites + environment variables
  - iOS steps (pairing, route selection, troubleshooting)
  - backend steps (start server, seed data, smoke requests)
  - “known good” demo scripts (3-5 commands)
  - rollback/fallback steps (switch to phone speaker, disable push)
- Mirror doc in `work/` for iteration tracking.

## Acceptance criteria
- Runbook includes a start-to-finish checklist that a new person can follow.
- Includes at least 5 common failure modes with diagnosis steps.
- References the existing endpoints:
  - `POST /v1/command`
  - `POST /v1/tts`
  - `GET /v1/notifications` and `GET /v1/notifications/{notification_id}`
- No code changes.

## Notes
- Prefer phone mic capture; do not assume programmatic access to glasses microphone.
