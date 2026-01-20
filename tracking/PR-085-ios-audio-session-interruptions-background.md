# PR-085: iOS audio session interruptions + background hardening

## Goal
Harden the iOS audio session so TTS playback and glasses routing survive common interruptions (phone calls, Siri, notifications) and behave correctly when the app backgrounds/foregrounds.

## Context
Docs and runbooks repeatedly call out iOS audio session interruptions and background audio limitations as a demo-risk for MVP4 (push-enabled assistant):
- `docs/ios-rayban-implementation-queue.md`
- `docs/ios-rayban-troubleshooting.md`
- `docs/meta-ai-glasses-audio-routing.md`

We already have route monitoring (e.g., PR-047), but we need a concrete, end-to-end implementation in the mobile app/native module that:
- observes interruptions
- pauses/resumes safely
- re-activates the audio session
- avoids falling back to speaker unexpectedly

## Scope
- Add/finish iOS interruption handling:
  - observe `AVAudioSession.interruptionNotification`
  - handle begin/end events (pause playback/recording; resume when allowed)
  - ensure `AVAudioSession` is re-activated after interruption ends
- Background/foreground hardening:
  - handle app lifecycle events to re-apply desired audio session category/mode/options
  - document required iOS capabilities (Background Modes → Audio) if needed for the chosen behavior
- Improve observability:
  - add lightweight logging hooks (dev-only) so diagnostics can show last interruption + route

## Non-goals
- True always-listening background capture.
- Full push-notification feature work (that’s tracked elsewhere); this PR is about audio session stability.

## Acceptance criteria
- While playing TTS via the glasses route:
  - a simulated interruption (Siri/phone call) pauses cleanly and does not crash
  - after interruption ends, audio session is re-activated and playback can resume
  - route does not permanently fall back to speaker
- Docs include a small manual test checklist for the above.

## Suggested files
- `mobile/modules/expo-glasses-audio/ios/GlassesPlayer.swift`
- `mobile/modules/expo-glasses-audio/ios/ExpoGlassesAudioModule.swift`
- Mobile screen used for playback (e.g. diagnostics) if it needs lifecycle wiring
- Relevant docs under `docs/ios-rayban-*.md`

## Validation
- Manual on-device test (iPhone + Bluetooth glasses/headset).
- Follow the manual test checklist in `docs/ios-audio-interruption-testing.md`.

