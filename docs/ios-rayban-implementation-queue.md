# iOS + Ray-Ban Meta implementation queue

This document is the recommended execution order for getting to an end-to-end MVP1 demo on iOS with Ray-Ban Meta glasses as the audio device.

## Definitions
- **MVP1 demo**: speak → command → inbox summary → TTS spoken back through glasses.
- **Reliable demo**: supports fallback to phone mic recording while still playing TTS through glasses.

## Queue (recommended order)

### Stage 0 — Backend ready (already present)
- Ensure backend is reachable: `GET /v1/status`.
- Ensure command loop works with text: `POST /v1/command`.
- Ensure TTS endpoint returns playable audio: `POST /v1/tts`.

Verification
- Text command returns `CommandResponse` with non-empty `spoken_text`.
- TTS response can be played locally on a laptop.

### Stage 1 — iOS audio output to glasses (lowest risk)
Goal
- Make sure audio output routes to the Bluetooth headset (glasses) reliably.

Verification
- Play a short test WAV; confirm it plays on the glasses.
- Show the current route (speaker vs bluetooth) in a diagnostics UI.

### Stage 2 — iOS audio capture (with fallback)
Goal
- Record audio with a best-effort preference for headset mic, but a strong fallback to phone mic.

Verification
- Record a short clip, save it, and play it back.
- Confirm recording works even if the headset mic is unavailable.

### Stage 3 — Audio upload + `/v1/command` as audio input
Goal
- Use the dev loop: upload base64 audio to `POST /v1/dev/audio`, then call `POST /v1/command` with an `audio` input URI.

Verification
- The backend accepts the audio input and returns a successful response.
- If STT is stubbed, it should still produce a deterministic transcript.

### Stage 4 — TTS playback through glasses (end-to-end)
Goal
- Use `spoken_text` → `/v1/tts` → play bytes through glasses.

Verification
- A spoken inbox summary is audible through the glasses.

### Stage 5 — Confirmations + safety (MVP3 readiness)
Goal
- Implement the mobile UI flow for confirmation and fallback buttons.

Verification
- A side-effect command returns `needs_confirmation` and can be confirmed via `/v1/commands/confirm`.

## Environment flags (backend)
STT
- `HANDS_FREE_STT_PROVIDER=stub` (default dev)
- `HANDS_FREE_STT_PROVIDER=openai` + `OPENAI_API_KEY=...` (more realistic)
- `HANDSFREE_STT_ENABLED=false` (force text path)

TTS
- `HANDSFREE_TTS_PROVIDER=stub` (default dev)
- `HANDSFREE_TTS_PROVIDER=openai` + `OPENAI_API_KEY=...`

GitHub
- `GITHUB_LIVE_MODE=true` + `GITHUB_TOKEN=...` for simple live mode.

## References
- MVP1 runbook: tracking/PR-059-ios-rayban-mvp1-demo-runbook.md
- OpenAPI contract: spec/openapi.yaml
