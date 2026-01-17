# PR-038: Mobile end-to-end voice demo hardening (record -> upload -> /v1/command -> TTS playback)

## Goal
Make the mobile app reliably demonstrate the core loop without needing glasses hardware:
1) record audio (push-to-talk)
2) upload to backend dev audio endpoint (`POST /v1/dev/audio`)
3) send audio command (`POST /v1/command` with `input.type=audio`)
4) play TTS result (`POST /v1/tts`) using phone speaker

## Why
This is the primary MVP demo path described in the implementation plan (MVP1) and unblocks iterative testing.

## Scope
- Mobile app only (no backend changes required unless strictly necessary)
- Focus on dev-mode path (local backend)

## Acceptance criteria
- `npm start` in `mobile/` + local backend running:
  - user can tap-and-hold to record (or tap-to-start/tap-to-stop)
  - on release, audio is uploaded to `/v1/dev/audio`
  - app submits `POST /v1/command` using returned `file://...` URI
  - app fetches `/v1/tts` for `spoken_text` and plays it
  - shows transcript + intent + status in a debug panel when dev toggle is enabled
- Error UX:
  - clear messages for backend unreachable, dev-mode disabled (403), upload failure, STT disabled

## Suggested implementation steps
- Ensure `mobile/src/api/client.js` uses `client_context.device`, `app_version`, `privacy_mode` per OpenAPI.
- Use a single “Command session” screen with:
  - record button
  - transcript/intent display
  - last response text
  - play/stop audio controls
- Keep secrets out of logs; rely on `X-User-ID` fixture header.

## Notes
- Backend already supports `/v1/dev/audio` (dev-only) and `/v1/command` audio via URI.
- Prefer minimal deps; use Expo/React Native built-ins where possible.
