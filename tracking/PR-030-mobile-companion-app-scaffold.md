# PR-030: Mobile companion app scaffold (iOS + Android)

## Goal
Add a starter mobile workspace scaffold (kept lightweight) to unblock building the real iOS/Android companion apps that will talk to the existing backend.

## Background
The backend already supports:
- `POST /v1/command` (text and audio URIs)
- `POST /v1/commands/confirm`
- `GET /v1/status`
- `POST /v1/tts`
- push subscription management via `/v1/notifications/subscriptions`

What’s missing is the actual mobile client implementation (out-of-repo today). This PR creates a minimal scaffold inside this repo so Copilot agents can iteratively implement and validate client flows without blocking on a separate repo setup.

## Scope
- Add `mobile/` workspace skeleton suitable for iOS + Android.
- Provide a minimal client architecture:
  - config (base URL, auth/session headers)
  - API client wrapper
  - basic screens: status, push-to-talk placeholder, “send text command” dev panel
  - confirmation UX: confirm/cancel/repeat/next
  - TTS playback wiring (fetch bytes + play)
- Keep the backend test suite unaffected.

## Non-goals
- Full production Bluetooth integration in this repo.
- App Store / Play Store release packaging.

## Acceptance criteria
- `mobile/README.md` provides a step-by-step local dev loop.
- The scaffold can:
  - call `GET /v1/status`
  - send a text command to `POST /v1/command`
  - handle a confirmation response via `POST /v1/commands/confirm`
  - fetch/play TTS from `POST /v1/tts`
- No changes required to backend CI beyond ignoring the `mobile/` folder.

## Suggested implementation approach
- Use Expo/React Native unless there’s a strong reason not to.
- Keep dependencies minimal; prefer platform SDKs and stable libraries.
- Store secrets/tokens using platform keystore (later PR).

## Agent checklist
- [ ] Create the `mobile/` scaffold and docs
- [ ] Implement minimal API client + dev panel flows
- [ ] Add confirmation UX primitives (confirm/cancel/repeat/next)
- [ ] Ensure nothing breaks Python tests
