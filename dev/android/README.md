# Android (Termux) Dev Tools

## Phone-local GitHub dispatcher

This provides a tiny HTTP server that accepts `POST /dispatch` and creates GitHub issues in a target repo.

It is intended to run on an Android phone via Termux, and be called from the mobile app.

### Install (Termux)

- `pkg update -y`
- `pkg install -y python`

### Configure

Set environment variables:

- `export GITHUB_TOKEN=...`
- `export DISPATCH_REPO=owner/repo`
- `export PORT=8765` (optional)

### Run

- `python dev/android/termux_phone_dispatcher.py`

### Test from another machine on the same Wi‑Fi

- `curl -s http://<PHONE_IP>:8765/health | jq .`
- `curl -s -X POST http://<PHONE_IP>:8765/dispatch -H 'Content-Type: application/json' \
    -d '{"title":"test dispatch","body":"hello","labels":["handsfree"]}' | jq .`

### Mobile app

In the mobile app Developer Settings:
- Set “Phone dispatcher URL” to `http://<PHONE_IP>:8765`
- Tap “Test Phone Dispatch”
