# Mobile App

## Target Platforms for First Demo
- **iOS** (iPhone) - Primary mobile platform
- **Meta AI Glasses** (Ray-Ban Meta Smart Glasses) - Primary wearable device

## Responsibilities
- Connect to Meta AI glasses via Bluetooth for audio I/O
- Connect to Apple Watch via the official wearable toolkit (future alternative)
- Capture audio from Meta AI glasses microphones (and optional images via camera if SDK available)
- Trigger STT (on-device or backend)
- Render minimal UI: status, last command, "Confirm" button (backup)
- Play TTS audio responses through Meta AI glasses speakers
- Receive push notifications and speak summaries through glasses

## Dev-first UX patterns
- Push-to-talk (MVP): press button on Meta AI glasses or hold button on phone
- Quick confirms: "confirm", "cancel", "repeat"
- "Dev mode" toggle:
  - route audio through the phone mic/speaker (bypass glasses)
  - show transcript + parsed intent in a debug panel
  - allow replay of canned transcripts (fixtures)

## Interfaces
- POST /v1/command (audio or text)
- GET /v1/status
- Push channel (APNS/FCM) -> in-app handler -> speak through glasses

## Testing
- Audio pipeline tests (gym noise simulations with Meta glasses)
- Bluetooth connection stability tests
- Latency benchmarks (glasses → phone → backend → phone → glasses)
- Permission and reconnect tests
- Simulator compatibility tests (mock Bluetooth audio for testing without hardware)
