# PR-024: Push notifications via APNS/FCM scaffolding

## Goal
Add the backend scaffolding needed for mobile clients to register push tokens and for the server to select a provider capable of APNS/FCM delivery.

## Background
The repo has:
- a notifications abstraction
- a working WebPush provider

What’s missing for mobile is the APNS/FCM-specific device registration + delivery provider plumbing.

## Scope
- Add API endpoint(s) for device push registration (store per-user device token + platform).
- Add DB persistence for device registrations (DuckDB table + migrations).
- Extend notification delivery provider selection to include APNS/FCM stubs (implementation can be placeholder, but interfaces must be real).
- Document required env vars/config for later production hardening.

## Non-goals
- Full production credential setup for APNS/FCM.
- Client-side implementation.

## Acceptance criteria
- Mobile clients can register/unregister a push token via the API.
- Device registrations are persisted and can be queried/admin-debugged.
- Notification provider selection supports APNS/FCM as named providers (even if stubbed initially).
- Tests remain green.

## Notes / Pointers
- Notifications: `src/handsfree/notifications/*`
- Existing polling notifications endpoint: `/v1/notifications` in `src/handsfree/api.py`
