# PR-030: Mobile companion app scaffold (iOS + Android)

## Status
Queued for Copilot agent implementation.

## Goal
Add a minimal `mobile/` scaffold (Expo/React Native) that can:
- call `GET /v1/status`
- send text commands to `POST /v1/command`
- handle confirmation via `POST /v1/commands/confirm`
- fetch/play TTS from `POST /v1/tts`

## Notes
Keep backend CI green; if needed, exclude `mobile/` from Python tooling.
