# PR-037: Mobile audio capture + upload (dev) -> send audio command

## Goal
Enable the Expo mobile client in `mobile/` to capture voice audio and submit it as an **audio command** to the backend.

This PR is meant to complete the dev loop:
1) record audio on device
2) upload audio bytes to the backend dev endpoint (base64)
3) receive a `file://` URI
4) call `POST /v1/command` with `{ "input": {"type": "audio", "uri": "file://..."} }`

## Background
Backend support exists (or is landing) via:
- `POST /v1/dev/audio` (dev-only): accepts base64 audio, writes to dev audio dir, returns `file://` URI
- Existing audio URI ingestion path already supports `file://` in dev

## Scope
- Add a minimal audio recorder UI in `mobile/`:
  - press-to-record / stop
  - shows duration and file size
  - allows sending as a command

- Implement client-side upload and command submission:
  - encode recorded audio bytes as base64
  - call `POST /v1/dev/audio` to obtain `uri`
  - call `POST /v1/command` with audio input

- Document a smoke test procedure.

## Non-goals
- Production-grade audio upload (object storage, pre-signed URLs)
- Background recording support
- Bluetooth routing reliability (handled by separate glasses routing work)

## Acceptance criteria
- From a real device or emulator, you can:
  - record a short clip
  - upload it to `POST /v1/dev/audio`
  - submit it to `POST /v1/command` as an audio input
  - see a valid `CommandResponse` and optionally play TTS

## Notes / pointers
- Mobile API wrapper: `mobile/src/api/client.js`
- Backend OpenAPI: `spec/openapi.yaml`
- Dev endpoint (if enabled): `src/handsfree/api.py`

## Agent checklist
- [ ] Add audio record UI and recording implementation
- [ ] Implement base64 upload to `POST /v1/dev/audio`
- [ ] Wire audio URI into `POST /v1/command`
- [ ] Update mobile docs with a smoke test
