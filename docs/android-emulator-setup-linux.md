# Android Emulator Setup (Linux)

This repo supports an **emulator-first** development workflow for UI + network integration.

Important: Android emulators are **not a substitute** for real Bluetooth device validation (e.g., Meta AI glasses). Use the emulator to validate:
- the app boots
- it can reach the backend (`/v1/status`)
- it can upload simulated audio
- it can invoke phone dispatcher calls (if you run a local dispatcher)

Then switch to a **physical Android phone** for Bluetooth + real audio routing.

## Prerequisites

- Linux host with hardware virtualization enabled
- Android Studio + SDK tools installed
- AVD created (recommended: Pixel 7 or similar, x86_64)

## KVM / hardware acceleration

The Android Emulator on Linux is dramatically more reliable with KVM.

1) Verify virtualization is enabled:

- Intel: `egrep -c '(vmx)' /proc/cpuinfo`
- AMD: `egrep -c '(svm)' /proc/cpuinfo`

2) Verify `/dev/kvm` exists:

- `ls -l /dev/kvm`

3) Ensure your user can access it:

- `groups` should include `kvm`
- If not: `sudo usermod -aG kvm $USER` then log out/in

## Create an AVD

Recommended baseline:
- Device: Pixel 7 (or similar)
- System image: Android 14+ (Google APIs)
- ABI: x86_64

## Backend connectivity from emulator

From inside the emulator:
- `http://10.0.2.2:<port>` reaches **your host machine**.

In this repo, the backend default is `8080`, so:
- `http://10.0.2.2:8080`

Alternative approach (USB / real device): `adb reverse` is often simpler.

## App configuration tips

- In the mobile app settings, set backend URL to `http://10.0.2.2:8080` (emulator).
- Enable **Simulate glasses audio** to validate the audio pipeline without Bluetooth.

## Troubleshooting

- Emulator is extremely slow
  - KVM likely not enabled (see section above)
- App cannot reach backend
  - Confirm backend is listening on `0.0.0.0:8080` (not just `localhost` inside container)
  - Try `curl http://localhost:8080/v1/status` on host, then `curl http://10.0.2.2:8080/v1/status` from emulator browser

## Next

- See `docs/android-emulator-smoke-workflow.md` for a quick sanity loop.
- See `docs/android-device-workflow.md` for real phone setup.
