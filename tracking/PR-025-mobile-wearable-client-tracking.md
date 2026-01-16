# PR-025: Mobile/wearable client work tracking (docs-only)

## Goal
Capture the MVP mobile + wearable deliverables as a concrete checklist and define the integration points to the backend.

## Background
The backend is largely MVP-ready, but the plan requires a mobile/wearable client to:
- capture audio (wearable → phone)
- call `/v1/command` (audio/text)
- play TTS responses
- receive push notifications and speak summaries

This repo does not currently contain the mobile client implementation.

## Scope (docs-only in this repo)
- Create a clear checklist of mobile/wearable features:
  - wearable audio capture → phone bridge
  - push-to-talk UX and error handling
  - STT routing decision (on-device vs backend)
  - TTS playback (phone + wearable)
  - push notification receive + speak
  - dev-mode features (transcript/debug panel, replay fixtures)
- Document API contracts used:
  - `POST /v1/command`
  - `POST /v1/commands/confirm`
  - `GET /v1/status`
  - push registration endpoint(s) (from PR-024)
- Recommend repo/project separation (new mobile workspace) and CI strategy.

## Non-goals
- Implementing the mobile app in this repo.

## Acceptance criteria
- Tracking doc exists with a shippable checklist and clear API integration points.
- Identifies dependencies on backend PRs (notably PR-024 for push registration).
