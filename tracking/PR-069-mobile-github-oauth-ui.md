# PR-069: Mobile GitHub OAuth UI integration

## Goal
Make it possible to connect GitHub from the mobile app without manual token copying by wiring the backend OAuth flow into the mobile Settings UI.

## Why
Backend OAuth endpoints exist (`GET /v1/github/oauth/start`, `GET /v1/github/oauth/callback`), but the mobile app does not expose a "Login with GitHub" experience.

## Scope
Mobile-only changes under `mobile/` (plus any small doc updates if needed).

## Deliverables
- Settings UI button: **"Connect GitHub"**.
- On tap: call `GET /v1/github/oauth/start`, open returned authorization URL in system browser.
- Handle redirect back into the app (deep link) and complete the flow:
  - Call `GET /v1/github/oauth/callback?code=...&state=...` (or whatever callback contract requires).
  - Store returned `connection_id` (or equivalent) in AsyncStorage.
- Ensure subsequent API calls include the connection identifier / auth as needed.

## Acceptance criteria
- A user can connect GitHub in <60 seconds on a real device.
- After connecting, inbox and PR summary use live GitHub data (when backend is configured to prefer OAuth connections).
- Clear error handling for cancelled auth, bad state, or backend misconfiguration.

## Implementation notes
- Likely touch points:
  - Settings screen (Status/Config screen)
  - Add deep link config to `mobile/app.json` and app entry
  - API client in `mobile/src/api/`
- Prefer system browser over embedded WebView.

## Test plan
- Manual:
  - Verify happy path connect
  - Verify cancel path
  - Verify state mismatch shows a safe error
