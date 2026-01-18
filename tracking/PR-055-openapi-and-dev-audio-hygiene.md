# PR-055: OpenAPI sync + dev audio endpoint hygiene

## Goal
Reduce contract drift and eliminate confusing backend dev-loop behavior.

## Current gaps
- OpenAPI does not reflect some implemented endpoints (e.g. GitHub OAuth / connections, admin API keys).
- There are duplicate `POST /v1/dev/audio` handlers in the backend, which can cause surprising routing/behavior.

## Scope
- Reconcile `spec/openapi.yaml` with implemented FastAPI routes:
  - Either add missing paths to the spec, or remove/rename endpoints not meant to be public.
- Remove the duplicate `/v1/dev/audio` handler and keep a single canonical behavior.
- Add/adjust contract validation tests (or scripts) so drift is caught in CI.

## Acceptance criteria
- `scripts/validate_openapi.py` (or equivalent) passes.
- No duplicate route registration for `/v1/dev/audio`.
- Spec and implementation agree on documented endpoints.

## References
- spec/openapi.yaml
- src/handsfree/api.py
- scripts/validate_openapi.py
