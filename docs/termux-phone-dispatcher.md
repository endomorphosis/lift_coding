# Termux Phone Dispatcher

This repo supports an optional **phone-local dispatcher** for GitHub issue creation.

Motivation:
- keep GitHub tokens off the backend
- let the phone dispatch tasks directly over local network

## Server

See `dev/android/termux_phone_dispatcher.py`.

## Client

The mobile app calls this via `mobile/src/api/phoneDispatcher.js` and the Settings screen “Phone dispatcher URL”.

## Security notes

- Treat `GITHUB_TOKEN` as sensitive.
- Prefer fine-grained tokens scoped to a single repo with Issues write permission.
- Do not expose the dispatcher to the public internet.

### Optional shared secret

If you set `DISPATCHER_SHARED_SECRET` on the phone, the dispatcher will require:

- HTTP header: `X-Handsfree-Dispatcher-Secret: <value>`

The mobile client supports configuring this via `EXPO_PUBLIC_PHONE_DISPATCHER_SECRET` (or by storing a secret in local storage).

