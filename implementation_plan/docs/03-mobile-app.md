# Mobile App

## Responsibilities
- Connect to wearable via the official wearable toolkit
- Capture audio (and optional images)
- Trigger STT (on-device or backend)
- Render minimal UI: status, last command, “Confirm” button (backup)
- Play TTS audio responses through the wearable
- Receive push notifications and speak summaries

## Dev-first UX patterns
- Push-to-talk (MVP): hold button on phone or tap gesture (if available)
- Quick confirms: “confirm”, “cancel”, “repeat”
- “Dev mode” toggle:
  - route audio through the phone mic/speaker
  - show transcript + parsed intent in a debug panel
  - allow replay of canned transcripts (fixtures)

## Interfaces
- POST /v1/command (audio or text)
- GET /v1/status
- Push channel (APNS/FCM) -> in-app handler -> speak

## Testing
- Audio pipeline tests (gym noise simulations)
- Latency benchmarks
- Permission and reconnect tests
- Simulator compatibility tests (same flows as wearable I/O)
