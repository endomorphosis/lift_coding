# PR-033: Meta AI Glasses Bluetooth audio routing prototype (iOS + Android)

## Goal
Prototype and document the **Bluetooth audio routing** needed to use **Meta AI Glasses (Ray-Ban Meta Smart Glasses)** as the audio I/O device for the mobile companion app.

This PR focuses on the mobile-side audio pipeline:
- audio capture from the glasses mic (via Bluetooth headset input)
- audio playback to the glasses speakers (via Bluetooth headset output)
- stable session management across background/foreground and interruptions

## Background
The backend already supports the command loop and TTS:
- `POST /v1/command` (text + audio URIs)
- `POST /v1/tts` (audio response)

What’s missing is the phone ↔ glasses audio session plumbing and UX patterns that make hands-free usage reliable.

## Scope
- Add a dedicated integration guide:
  - iOS: `AVAudioSession` category/mode/options for Bluetooth headset input/output
  - Android: audio routing with `AudioManager` and Bluetooth SCO/headset profiles
  - recommended codecs/sample rates and how to convert to backend-accepted formats
- Add a minimal “audio diagnostics” scaffold under `mobile/`:
  - show current route (speaker vs bluetooth)
  - record a short clip and play it back through the current route
  - export captured audio for inspection
- Document known failure modes + mitigations:
  - route changes, interruptions (phone calls), permissions
  - reconnect behavior
  - latency/echo handling

## Non-goals
- Shipping a production Bluetooth stack in Python.
- Vendor SDK integrations beyond standard OS Bluetooth audio routing.

## Acceptance criteria
- New doc exists: `docs/meta-ai-glasses-audio-routing.md`.
- `mobile/glasses/` contains a small scaffold/README for an audio diagnostics screen.
- Clear checklist to validate end-to-end: glasses mic -> phone -> backend -> phone -> glasses.
- No impact to backend tests.

## Agent checklist
- [ ] Write `docs/meta-ai-glasses-audio-routing.md`
- [ ] Add `mobile/glasses/README.md` + placeholder structure for diagnostics
- [ ] Include iOS + Android routing guidance and gotchas
