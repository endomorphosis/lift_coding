# PR-118: Dev docs port + dev-audio payload alignment

## Goal
Remove “it works on my machine” friction when bringing up the backend and the mobile/dev tooling by aligning documentation and the dev audio upload payload with the actual running defaults.

## Why
- The backend runs on port `8080` by default (local `make dev`, Docker, and OpenAPI), but several runbooks/docs still referenced `8000`.
- `/v1/dev/audio` is specified (and implemented) to accept `data_base64`, while some docs/clients referenced other field names.

## Acceptance criteria
- User-facing docs and runbooks consistently use `http://localhost:8080` for the backend.
- Dev audio upload examples use `data_base64`.
- Backend tolerates `audio_base64` as an alias for `data_base64` to avoid breaking older clients.
