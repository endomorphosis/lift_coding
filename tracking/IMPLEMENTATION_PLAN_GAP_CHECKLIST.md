# Implementation Plan Gap Checklist (Backend vs Client)

This checklist aligns the plan's MVP1–MVP4 items to what is already implemented in this repository vs what remains to be built (often in a separate mobile/wearable repo).

## MVP1: Read-only PR inbox

- [x] Backend endpoint(s) and contract for command submission (text/audio metadata): `/v1/command`.
- [x] Inbox intent parsing and routing (`inbox.list`).
- [x] GitHub read provider (fixtures + live), inbox composition.
- [x] Webhook ingestion + replay tools for GitHub events.
- [x] Basic audit/action logging patterns.
- [x] Dev simulator: browser-based mic -> `/v1/command` -> TTS playback.

Remaining (backend):
- [x] Production audio input fetch: support `https://` audio URIs (pre-signed URLs) with allowlists, size/time limits, and safe error handling. ✅ Implemented in PR-020
- [x] Push delivery provider beyond dev logger (e.g., WebPush/APNS/FCM integration). ✅ Implemented in PR-015 (WebPush) and PR-024 (APNS/FCM scaffolding)

Remaining (client-side / out of repo):
- [ ] Wearable audio capture -> mobile (or phone) pipeline.
- [ ] Playback of TTS audio on device/wearable.
- [ ] Push notification receive + user controls.

## MVP2: PR summary

- [x] `pr.summarize` intent and summary response shape.
- [x] “repeat/next” navigation primitives (server-side).

Remaining (backend):
- [x] Profile-based verbosity tuning (Workout/Commute/Kitchen/Focused/Relaxed) for spoken text, summaries, and inbox filtering. ✅ Implemented + covered by tests (PR-027 scope)

Remaining (client-side):
- [ ] UX for “repeat/next” and quick confirms in mobile/wearable app.

## MVP3: One safe write action

- [x] Side-effect actions are policy-gated + confirmation supported.
- [x] Rate limiting and audit patterns exist.
- [x] At least one write action implemented (request review / rerun checks / merge) behind policy.

Remaining (backend):
- [x] Tighten auth story for production clients (API keys or session tokens) if needed. ✅ Implemented in PR-018 (API key auth) and PR-023 (GitHub OAuth)

## MVP4: Agent delegation

- [x] `agent.delegate` intent exists.
- [x] Agent task persistence + lifecycle state model exist.
- [x] Dev-only endpoints exist to drive task transitions.
- [x] Agent intents use authenticated `user_id` end-to-end (removed "default-user" placeholder usage).

Remaining (backend):
- [x] Replace placeholder agent provider with a real integration (e.g., dispatcher that creates a GitHub issue/PR work item, plus correlation to webhook events to mark completion). ✅ Implemented in PR-016 (github_issue_dispatch provider with webhook correlation)
- [x] Notifications on agent task state changes via push subscriptions (auto-delivery + provider selection). ✅ Implemented via notifications auto-push + platform providers

Remaining (client-side / out of repo):
- [ ] iOS + Android companion apps that integrate with Meta AI Glasses for audio capture/playback.
- [ ] Register APNS/FCM tokens and handle push receive -> speak via TTS on-device.

Remaining (external / infra):
- [ ] A real agent runner (Copilot agent, workflow automation, or custom runner) that can act on dispatched tasks.

