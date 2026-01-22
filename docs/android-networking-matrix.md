# Android Networking Matrix (Emulator vs Device)

This doc exists to answer one recurring question: **what backend URL should the mobile app use** in each setup?

## Quick matrix

| Setup | Backend runs where | Mobile runs where | Recommended app Backend URL | Notes |
|---|---|---|---|---|
| Android emulator | Host machine (python or docker) | Emulator | `http://10.0.2.2:8080` | `10.0.2.2` is the emulator’s view of the host |
| Physical Android phone (USB) | Host machine (python or docker) | Phone | `http://localhost:8080` | Use `adb reverse tcp:8080 tcp:8080` |
| Physical Android phone (Wi‑Fi) | Host machine (python or docker) | Phone | `http://<HOST_LAN_IP>:8080` | Host firewall must allow inbound 8080 |

## Emulator notes

- `10.0.2.2` is **special**: it maps to the host’s loopback from inside the emulator.
- If your backend is in Docker and publishes `8080:8080`, the host still owns port 8080, so `10.0.2.2:8080` should work.

## Device notes

### adb reverse (recommended)

- `adb reverse tcp:8080 tcp:8080`

Then the phone can use `http://localhost:8080` and the traffic goes over USB.

### Wi‑Fi (LAN)

Use `http://<HOST_LAN_IP>:8080`.

Common failures:
- backend bound only to `127.0.0.1` (this repo uses `0.0.0.0` by default)
- firewall blocks inbound 8080
- phone and host are on different networks

## Bluetooth accessories

Bluetooth passthrough in emulators is not reliable for real devices like Meta AI glasses.
Use a **physical phone** for Bluetooth/audio routing validation.
