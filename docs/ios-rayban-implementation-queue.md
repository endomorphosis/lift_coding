# iOS + Ray-Ban Meta implementation queue

This document is the recommended execution order for getting to an end-to-end MVP1 demo on iOS with Ray-Ban Meta glasses as the audio device.

## Definitions
- **MVP1 demo**: speak → command → inbox summary → TTS spoken back through glasses.
- **Reliable demo**: supports fallback to phone mic recording while still playing TTS through glasses.

## Queue (recommended order)

### Stage 0 — Backend ready
Goal
- Backend reachable and demoable via text + TTS.

Verification
- `GET /v1/status` succeeds.
- `POST /v1/command` (text) returns `spoken_text`.
- `POST /v1/tts` returns playable audio.

### Stage 1 — iOS audio output routes to glasses
Goal
- Ensure audio output routes to the Bluetooth headset (glasses) reliably.

Verification
- Play a short test audio clip; confirm it plays on the glasses.
- Display current audio route in a diagnostics screen.

### Stage 2 — iOS audio capture (with fallback)
Goal
- Record audio with best-effort headset mic preference but strong fallback to phone mic.

Verification
- Record a short clip and play it back.
- Confirm recording works when headset mic is unavailable.

### Stage 3 — Upload audio + command as audio input
Goal
- Use `POST /v1/dev/audio` (base64 upload) and then call `POST /v1/command` with an `audio` input URI.

Verification
- Backend accepts audio input and returns a successful response.

### Stage 4 — TTS playback through glasses (end-to-end)
Goal
- Use `spoken_text` → `/v1/tts` → play bytes through glasses.

Verification
- A spoken inbox summary is audible through the glasses.

### Stage 5 — Confirmations + safety
Goal
- Support confirmation flows for side-effectful actions.

Verification
- Side-effect command returns `needs_confirmation` and can be confirmed via `/v1/commands/confirm`.

## References
- MVP1 runbook: tracking/PR-059-ios-rayban-mvp1-demo-runbook.md
- OpenAPI contract: spec/openapi.yaml
