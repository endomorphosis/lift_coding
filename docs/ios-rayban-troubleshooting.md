# iOS + Ray-Ban Meta troubleshooting

This guide is optimized for fast recovery during demos.

## Triage (fast path)
1) Confirm the glasses are connected as a Bluetooth audio device.
2) Confirm **output route** is the glasses (not speaker).
3) If mic input is flaky, **switch to phone mic** (do not block the demo).
4) Retry playback through glasses.

## Common symptoms and fixes

### Output plays on speaker, not glasses
- Reconnect Bluetooth.
- Re-activate the audio session in the app.
- Toggle audio route (if the app provides a route picker).

### No headset mic input (or very low quality)
- Prefer a fallback policy:
  - use phone mic recording
  - keep output routed to glasses
- Avoid blocking the demo on headset mic input.

### Route changes mid-session
- Handle interruptions explicitly:
  - phone call, Siri, notifications
  - background/foreground transitions

### Backend rejects audio input
- Confirm the format is one of: wav/m4a/mp3/opus.
- For dev, prefer the `POST /v1/dev/audio` flow (base64 upload → `file://` URI).

## Suggested diagnostics to display in-app
- Current output route (speaker/bluetooth/headphones)
- Current input source (built-in mic vs headset)
- Sample rate, channel count, encoding
- Last upload size + duration
- Last backend response status + `spoken_text`

## References
- MVP1 runbook: tracking/PR-059-ios-rayban-mvp1-demo-runbook.md
- OpenAPI contract: spec/openapi.yaml
