# PR-042: OpenAPI contract sync for notifications endpoints

## Goal
Bring `spec/openapi.yaml` back into alignment with the actually implemented notifications API.

## Current Problem
The backend implements:
- `GET /v1/notifications`
- `GET /v1/notifications/subscriptions`
- `POST /v1/notifications/subscriptions`
- `DELETE /v1/notifications/subscriptions/{subscription_id}`

…but `spec/openapi.yaml` currently does **not** define these routes. This breaks client generation and contract tests/validation for consumers.

## Scope
- Add missing `paths:` entries for the notifications endpoints.
- Ensure schemas referenced match existing response models (or add new schemas if missing).

## Non-goals
- Changing backend behavior.
- Adding push delivery behavior (this is contract-only).

## Acceptance Criteria
- `make openapi-validate` passes.
- `spec/openapi.yaml` includes all implemented notifications routes.

## Implementation Notes
- Prefer referencing existing schemas under `components/schemas` when possible.
- If backend responses include auth requirements, document `401` responses consistently with other endpoints.

## Files
- `spec/openapi.yaml`
- Potentially `tests/test_api_contract.py` (only if it currently assumes the old spec)
