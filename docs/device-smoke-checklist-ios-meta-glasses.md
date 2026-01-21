# Device Smoke Checklist (iOS + Meta AI Glasses)

This is a quick, copy/paste checklist for validating end-to-end on a physical iPhone with Meta AI Glasses.

## Prereqs

- Backend reachable from your iPhone over LAN at port **8080**.
- Mobile app built as an **Expo development build** (Expo Go will not load native modules).
- iPhone paired to Meta AI Glasses via iOS Bluetooth settings.

## 1) Backend: health check (from your laptop)

```bash
curl -sS http://localhost:8080/v1/status | cat
```

If testing from a phone, use your laptop’s LAN IP (example):

```bash
export BACKEND_URL="http://192.168.1.10:8080"
curl -sS "$BACKEND_URL/v1/status" | cat
```

If this fails:
- Make sure the backend is listening on `0.0.0.0:8080` (not only `127.0.0.1`).
- Open firewall for TCP 8080 on your laptop.

## 2) Backend: dev audio upload endpoint

The dev endpoint is `POST /v1/dev/audio` and expects `data_base64`.

```bash
# Create a tiny test payload (base64 of the string "test")
export BACKEND_URL="http://192.168.1.10:8080"
export B64="dGVzdA=="

curl -sS -X POST "$BACKEND_URL/v1/dev/audio" \
  -H 'Content-Type: application/json' \
  -d '{"data_base64":"'"$B64"'","format":"wav"}' | cat
```

Expected: JSON response with a `uri`.

## 3) Mobile: install/run an iOS dev build

From `mobile/` on a Mac with Xcode:

```bash
cd mobile
npm ci
npx expo run:ios --device
```

(If you’re using EAS, install the development build .ipa and then run `npx expo start --dev-client`.)

## 4) Mobile: configure backend URL

On the iPhone app:
- Open **Settings** tab.
- Set Base URL to `http://<YOUR_LAPTOP_LAN_IP>:8080`.
- Confirm `GET /v1/status` works (if the UI exposes status) or proceed to the diagnostics flow.

## 5) Glasses: validate Bluetooth routing

On iPhone:
- Settings → Bluetooth → confirm glasses are connected.

In the app:
- Open **Glasses Diagnostics**.
- Confirm the native module is available (development build required).
- Confirm the audio route shows Bluetooth/glasses as the active input/output when in “glasses mode”.

## 6) Record → upload → command pipeline (dev)

In **Glasses Diagnostics** (or whichever screen drives the flow), run:
1. Record a short clip.
2. Upload to `POST /v1/dev/audio`.
3. Send to `/v1/command`.
4. (Optional) TTS/playback if enabled.

If upload fails:
- Ensure the payload field is `data_base64` (not `audio_data`).
- Ensure your backend auth mode allows dev uploads (common: `HANDSFREE_AUTH_MODE=dev`).

## Troubleshooting quick hits

- **“Native module not available”**: you’re in Expo Go; rebuild as dev-client.
- **Cannot reach backend from phone**: wrong IP, firewall, or backend only bound to localhost.
- **iOS local HTTP blocked**: ensure ATS local-network allowance is enabled in the app config.
