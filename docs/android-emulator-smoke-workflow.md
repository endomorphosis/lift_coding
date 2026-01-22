# Android Emulator Smoke Workflow

This is a lightweight “first pass” workflow to validate:
- mobile app boots
- mobile app can reach the backend
- simulated audio + command flows work end-to-end

It does **not** validate Bluetooth accessories (e.g., Meta glasses).

## 1) Start backend

From repo root:

- `docker compose up -d`

Confirm backend:

- `curl http://localhost:8080/v1/status`

## 2) Start emulator

- Start your AVD from Android Studio, or:
  - `emulator -avd <AVD_NAME>`

## 3) Configure app settings

In the mobile app:

- Backend URL: `http://10.0.2.2:8080`
- Enable: **Simulate glasses audio**

## 4) Validate

Suggested checks:
- Status screen shows backend as reachable
- “record → upload” path works using simulated audio
- Any “dispatch via phone” calls are either disabled or point at a test dispatcher

## Optional: automate

A follow-up PR may add a helper script:
- `scripts/android_emulator_smoke.sh`

