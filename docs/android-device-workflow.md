# Android Device Workflow (Physical Phone)

Use this workflow when you need:
- real Bluetooth pairing / accessories (e.g., Meta AI glasses)
- realistic audio routing (mic input + playback)

The emulator is great for UI + network pipeline testing, but it is not a substitute for real Bluetooth + audio routing.

## 1) Start backend

From repo root:

- `docker compose up -d`

Confirm backend:

- `curl http://localhost:8080/v1/status`

## 2) Enable Android developer options

On your phone:
- Enable Developer options
- Enable USB debugging

Confirm ADB sees the device:

- `adb devices`

## 3) Connect the app to the backend

### Option A (recommended): adb reverse (USB)

This keeps the app pointing at `http://localhost:8080` while routing requests over USB.

- `adb reverse tcp:8080 tcp:8080`

Then in the app settings, you can use:
- Backend URL: `http://localhost:8080`

### Option B: LAN IP (Wi‑Fi)

If you prefer Wi‑Fi:

- Backend URL: `http://<YOUR_LINUX_HOST_IP>:8080`

Notes:
- Your host firewall must allow inbound connections to 8080
- Your backend must bind to `0.0.0.0` (not only `127.0.0.1`)

## 4) Glasses / Bluetooth validation

Pair the Meta AI glasses with your phone using the normal OS flow.

Then validate:
- the app can switch the audio source to “glasses”
- recording uses the intended mic
- playback routes correctly

## Helper script

See `scripts/android_device_connect.sh` for a small helper that applies `adb reverse`.
