# Android Emulator + Bluetooth + On-Device Python (Termux)

This doc covers two goals:

1) **Simulate Meta AI Glasses flows on an Android emulator** (for UI + backend/GitHub command pipeline).
2) **Run Python on an Android phone** (Termux) to dispatch GitHub tasks/commands.

## Reality check: Bluetooth in the Android emulator

The standard Android Studio Emulator **does not reliably support** Bluetooth Classic / BLE in a way that can emulate real hardware accessories like Meta AI Glasses (pairing, SCO routing, mic input/output).

Practical implication:
- **For real Bluetooth audio routing tests** (SCO, BT mic, BT speaker): use a **physical Android phone**.
- **For pipeline testing** (record → upload → command → TTS → playback): emulator is still very useful if you use the phone mic/speaker (i.e., “DEV mode” style flows).

## Recommended setup options

### Option A (recommended): Physical Android phone for Bluetooth

- Build a dev-client and test with real Bluetooth pairing.
- This is the only path that meaningfully validates audio routing.

### Option B: Android emulator for end-to-end command pipeline (no real Bluetooth)

Use the emulator to validate:
- App UI
- Network connectivity to backend (`/v1/status`)
- Audio upload (`/v1/dev/audio`)
- Command handling (`/v1/command`)
- TTS playback (device speaker)

You will *not* validate:
- Bluetooth pairing
- SCO routing
- Real glasses mic/speaker paths

## Run backend + test from emulator

Backend health:

```bash
curl http://localhost:8080/v1/status
```

From Android Emulator, your laptop’s `localhost` is reachable at `10.0.2.2`:

- Set Mobile Base URL to `http://10.0.2.2:8080`

## Run Python on Android (Termux) to dispatch GitHub commands

This repo’s backend already supports GitHub task dispatch (see `github_issue_dispatch` provider), but if you want a **phone-local Python dispatcher**, Termux is the fastest way.

### Termux install (on Android phone)

1) Install **Termux** (F-Droid recommended).
2) In Termux:

```bash
pkg update
pkg install python git
pip install --upgrade pip
pip install httpx
```

### Run the dispatcher

Use the script in `dev/android/termux_github_dispatcher.py`.

```bash
export GITHUB_TOKEN="<your_pat>"
export DISPATCH_REPO="owner/repo"   # repo where issues will be created

python dev/android/termux_github_dispatcher.py --host 0.0.0.0 --port 8765
```

Test from a second shell (or from your laptop on the same LAN):

```bash
curl -sS -X POST http://<PHONE_IP>:8765/dispatch \
  -H 'Content-Type: application/json' \
  -d '{"title":"Test dispatch","body":"hello from phone","labels":["agent-task"]}' | cat
```

Security note:
- This is a minimal dev tool. Don’t expose it to the public internet.
- Prefer binding to LAN only and use strong GitHub tokens.

## Next step (if you want deeper simulation)

If you want emulator-based “glasses comms” simulation, the pragmatic approach is:
- Add a **simulated transport** in the mobile app (JS shim) that behaves like `expo-glasses-audio`, but uses mic/speaker and emits fake route changes.
- Keep the native Bluetooth path for real device testing.

If you want, I can implement that simulated transport as a follow-on PR.
