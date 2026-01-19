# iOS + Ray-Ban Meta Demo Runbook

This runbook is for the end-to-end “handsfree” demo on iOS with Ray-Ban Meta glasses, focusing on the reliable path: **phone mic input + Bluetooth output to glasses**.

## Acceptance Checklist (MVP)

- Backend reachable from phone: `GET /v1/status` succeeds.
- Mobile app can send a **text command** and render `spoken_text`.
- Mobile app can record a **dev audio command** and submit it via:
  - `POST /v1/dev/audio` (upload base64) → returns `file://…`
  - `POST /v1/command` with `input.type=audio` → returns `spoken_text`
- App can fetch TTS via `POST /v1/tts` and **play audio through the glasses**.

## Backend Setup

### Option A: Docker Compose

- Start services:
  - `docker compose up -d`
- API should be available at `http://localhost:8080`.

### Option B: Local Uvicorn

- Ensure `HANDSFREE_AUTH_MODE=dev` is set.
- Run the API:
  - `uvicorn handsfree.api:app --host 0.0.0.0 --port 8080`

## Mobile Setup (Expo)

### 1) Install dependencies

- From `mobile/`:
  - `npm ci` (uses the synced lockfile for reproducible builds)

### 2) Use a development build for native glasses diagnostics

The native glasses module does **not** work in Expo Go.

- Build a dev client:
  - `npx expo run:ios --device`

## Demo Flow

1. Pair Ray-Ban Meta glasses in iOS Bluetooth settings.
2. Launch the app.
3. In **Settings**:
   - Set Backend URL to your machine’s LAN IP, e.g. `http://192.168.1.10:8080`.
   - Optionally set a stable `X-User-ID`.
4. In **Status** tab:
   - Verify the backend is reachable.
5. In **Command** tab:
   - Send a text command (e.g. “what’s in my inbox?”).
   - Confirm TTS plays (should route to connected Bluetooth output).
6. In **Glasses Diagnostics** tab:
   - Start in DEV Mode if you want phone mic input.
   - Record → Send to backend → verify TTS playback.
   - Switch to Glasses Mode only if you’re testing native routing/monitoring.

## Troubleshooting

### Backend unreachable from phone

- Ensure phone and dev machine are on the same network.
- Use your machine’s LAN IP (not `localhost`).
- Confirm port `8080` is reachable (firewall/VPN can block).

### `POST /v1/dev/audio` returns 403

- Confirm `HANDSFREE_AUTH_MODE=dev` on the backend.
- Confirm the request uses `data_base64` (not `audio_base64`).

### Audio plays on phone, not glasses

- Confirm glasses are connected as an active audio output.
- Increase media volume.
- Toggle Bluetooth off/on.
- iOS can prefer A2DP output for media; if you force HFP/HSP for mic input you may get low-quality output.

### Glasses mic input is unreliable

For the MVP demo, prefer **phone mic** input (DEV mode) and route **output** to glasses.

## Optional: Push Notifications

If you want the “notify → speak” loop, wire up push subscription registration and handle notifications by fetching TTS for the notification text and playing it.
(Keep this as a follow-up unless it’s required for the demo.)
