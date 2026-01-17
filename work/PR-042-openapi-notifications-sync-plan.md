# PR-042: OpenAPI contract sync for notifications

## Status
Queued for Copilot agent implementation.

## Goal
Add the missing notifications endpoints to `spec/openapi.yaml` so contract validation and client generation match the backend.

## Checklist
- [ ] Add `GET /v1/notifications`
- [ ] Add `GET/POST/DELETE /v1/notifications/subscriptions`
- [ ] Ensure referenced schemas exist and match backend models
- [ ] Run `make openapi-validate`
