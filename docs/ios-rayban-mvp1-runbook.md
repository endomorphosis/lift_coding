# iOS + Ray-Ban Meta MVP1 runbook

This runbook is the “known-good” procedure for demoing HandsFree MVP1 with:
- iOS as the capture device (phone mic)
- Ray-Ban Meta glasses as the audio output device

## Prereqs
- iPhone paired to Ray-Ban Meta glasses (Bluetooth)
- Backend running locally or reachable over HTTPS

## Backend bring-up
1. Start API
2. Verify `GET /v1/status`
3. Verify `POST /v1/tts`
4. Verify `POST /v1/command` with text input

## iOS audio routing
- Ensure output is routed to the glasses (Bluetooth)
- If audio plays on phone speaker, toggle the route in iOS Control Center

## Demo script (recommended)
1) Inbox summary
2) PR summary
3) Ask to request review (should require confirmation)
4) Confirm
5) Ask “repeat”

## Troubleshooting
### Symptom: audio plays on phone, not glasses
- Check Bluetooth connection
- Toggle output route

### Symptom: STT returns stub text
- Ensure STT provider env vars are set

### Symptom: command returns 401
- Ensure auth mode is dev or the client is sending credentials

## Optional: notifications deep link
- Create a push subscription (Expo/APNS)
- Verify notification fetch + detail fetch
