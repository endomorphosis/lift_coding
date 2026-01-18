# PR-057 Work Plan

- [ ] Add DB helper to fetch a notification by id (scoped to user)
- [ ] Implement `GET /v1/notifications/{notification_id}` in the API
- [ ] Update OpenAPI spec for the new route
- [ ] Add tests for 200 + 404 behavior
- [ ] Run `python -m pytest -q` and `python scripts/validate_openapi.py`
