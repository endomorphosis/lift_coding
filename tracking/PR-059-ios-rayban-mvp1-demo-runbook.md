# PR-059: iOS + Ray-Ban Meta MVP1 demo runbook (end-to-end)

## Goal
Provide a single, actionable runbook that ties together the existing mobile/glasses work into an **end-to-end MVP1 demo**:

**Ray-Ban Meta glasses mic/speaker → iPhone → backend → iPhone → glasses speaker**

This PR is documentation-only in this repo.

## Why
We already have multiple mobile tracking PRs (recording, routing, playback, upload), but MVP readiness depends on:
- a clear demo sequence
- known-good backend environment flags
- crisp fallback behavior when Bluetooth mic routing is unreliable

## Scope
- Write a runbook that a developer can follow to demo MVP1 in <5 minutes.
- Document exact backend endpoints + expected payloads.
- Document backend environment flags for "realistic" STT/TTS vs stubs.
- Document known Ray-Ban Meta Bluetooth constraints and fallback behavior.

## Non-goals
- Implementing iOS code in this repo.
- Building a production push notification stack (polling is acceptable for MVP1).

## Demo definition (MVP1)
1) User speaks: "show my inbox"
2) Backend returns inbox summary + cards
3) iOS app calls TTS endpoint and plays audio through glasses
4) Optional: "summarize PR 123", "repeat", "next"

## Backend prerequisites
### Backend endpoints used
- Command loop: `POST /v1/command`
- Dev audio upload (optional): `POST /v1/dev/audio` (dev-only)
- TTS: `POST /v1/tts`
- Status: `GET /v1/status`
- Notifications (polling): `GET /v1/notifications?since=...` (optional)

See the contract in `spec/openapi.yaml`.

### Backend environment flags (recommended for demo)
- Auth mode for local dev: `HANDSFREE_AUTH_MODE=dev`

STT:
- Stub STT (deterministic transcript): `HANDS_FREE_STT_PROVIDER=stub`
- Realistic STT: `HANDS_FREE_STT_PROVIDER=openai` and `OPENAI_API_KEY=...`
- Disable STT (forces text input): `HANDSFREE_STT_ENABLED=false`

TTS:
- Stub TTS (deterministic WAV): `HANDSFREE_TTS_PROVIDER=stub`
- Realistic TTS: `HANDSFREE_TTS_PROVIDER=openai` and `OPENAI_API_KEY=...`

GitHub:
- Fixture-only (default): no env needed
- Live mode (simple demo): `GITHUB_LIVE_MODE=true` and `GITHUB_TOKEN=...`

Webhooks (optional):
- Dev signature accepted when secret unset; prod should set `GITHUB_WEBHOOK_SECRET`.

## Ray-Ban Meta (Bluetooth) constraints
- Treat the glasses primarily as **Bluetooth audio output**.
- Bluetooth mic input typically uses headset profiles and can be unreliable on iOS.
- MVP1 should support a fallback: **phone mic recording** while still playing TTS through the glasses.

## Demo runbook
### 0) Verify device routing
- Confirm the iPhone is paired to Ray-Ban Meta glasses and audio output routes to the headset.
- If routing is unstable, toggle Bluetooth or reselect the output route.

### 1) Verify backend is reachable
- Call `GET /v1/status`.

### 2) Trigger an inbox command
Option A (fastest, text path):
- Call `POST /v1/command` with `{"input": {"type": "text", "text": "show my inbox"}, ...}`

Option B (audio path, dev upload):
- Record audio on iOS (WAV/M4A/MP3/OPUS).
- Send base64 to `POST /v1/dev/audio` to receive a `file://...` URI.
- Call `POST /v1/command` with `{"input": {"type": "audio", "format": "m4a", "uri": "file://..."}, ...}`.

### 3) Play TTS through the glasses
- Take `spoken_text` from `CommandResponse`.
- Call `POST /v1/tts`.
- Play returned audio bytes via iOS audio session configured for Bluetooth output.

### 4) Navigation
- Send "next" (`system.next`) and "repeat" (`system.repeat`) via `POST /v1/command` text input.

### 5) Optional: PR summary
- Send "summarize PR 123".
- Play returned TTS.

## Related tracking PRs (implementation)
This runbook assumes implementation is delivered by these PRs:
- PR-033 (Meta AI glasses audio routing guide)
- PR-037 (Mobile audio capture + upload)
- PR-047 (iOS audio route monitor)
- PR-048 (iOS glasses recorder)
- PR-049 (iOS glasses player)

## Acceptance criteria
- A new doc exists in this repo that describes the end-to-end MVP1 demo.
- Runbook includes:
  - endpoints + payload shape references
  - backend env flags for STT/TTS/GitHub
  - fallback guidance for Bluetooth mic unreliability
- Runbook references the existing mobile tracking PRs instead of duplicating them.

## Agent checklist
- [ ] Create `tracking/PR-059-ios-rayban-mvp1-demo-runbook.md`
- [ ] Create `work/PR-059-ios-rayban-mvp1-demo-runbook.md`
- [ ] Create `docs/ios-rayban-mvp1-demo-runbook.md` with complete end-to-end demo instructions
