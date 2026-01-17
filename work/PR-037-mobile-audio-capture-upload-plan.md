# PR-037: Mobile audio capture + upload (dev) -> send audio command — execution plan

This PR is intended for a Copilot agent.

## Goal
Implement the missing mobile-side path for voice commands:
- record audio in the Expo app
- upload to backend dev endpoint `POST /v1/dev/audio`
- send audio command to `POST /v1/command`

## Suggested implementation (Expo-first)
1) Recording
- Use `expo-av` (`Audio.Recording`) to record linear PCM WAV if possible.
- If WAV is awkward in Expo, record to m4a and document/convert (dev-only), but prefer WAV to match backend expectations.

2) Upload
- Read file bytes (base64) and call `POST /v1/dev/audio` with:
  - `data_base64`
  - `format` (`wav` recommended)
- Use the returned `uri`.

3) Command submission
- Call existing `sendCommand()` equivalent with:
  - `input: { type: "audio", uri }`
  - plus `profile/client_context/idempotency_key`.

4) UX
- Add a simple "Record" panel to the Command screen:
  - Start/Stop recording
  - "Send audio" button
  - Show backend response + any `spoken_text`.

## Required backend settings (dev)
- `HANDSFREE_AUTH_MODE=dev` (so dev endpoints are enabled)
- Ensure the backend can read the saved `file://` audio path.

## Smoke test
- Start backend at `http://localhost:8080`
- Start mobile app with LAN access to backend
- Record 2–5 seconds
- Upload, then submit audio command

## Acceptance criteria
- End-to-end voice command works in dev without manually hosting audio files.
