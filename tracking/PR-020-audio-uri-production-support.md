# PR-020: Production audio URI support for /v1/command

## Goal
Support `https://` audio URIs (pre-signed URLs) safely for mobile clients.

## Background
The OpenAPI contract allows audio input via `uri`. The current implementation supports only local file paths / `file://` URIs.

## Scope
- Extend audio fetch to support `https://` URIs.
- Add safety controls:
  - allowlist/denylist of hosts
  - max content length
  - request timeouts
  - content-type validation
- Add unit tests using HTTP mocking.

## Non-goals
- Storing audio in the backend.
- On-device STT.

## Acceptance criteria
- `https://` audio URI works when host is allowed.
- Disallowed hosts and oversized payloads are rejected with clear errors.
- CI remains green.

