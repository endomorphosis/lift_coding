# Mobile Companion App (Scaffold)

This folder is a placeholder workspace for the eventual iOS + Android companion apps.

Backend integration targets:
- `GET /v1/status`
- `POST /v1/command`
- `POST /v1/commands/confirm`
- `POST /v1/tts`
- `GET /v1/notifications` (polling fallback)
- `/v1/notifications/subscriptions` (push registration)

## Status
Scaffold-only. Implementation is tracked in [tracking/PR-030-mobile-companion-app-scaffold.md](../tracking/PR-030-mobile-companion-app-scaffold.md).

## Next steps
- Implement an Expo/React Native app here (recommended) or native iOS/Android.
- Add a small API client wrapper that matches `spec/openapi.yaml`.
- Add a dev-mode panel to send a text command and render the response.
