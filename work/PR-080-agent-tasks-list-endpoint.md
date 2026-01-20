# PR-080 work log

## Checklist
- [ ] Locate agent task DB model + existing endpoints.
- [ ] Add DB query to list tasks by user_id with ordering.
- [ ] Add `GET /v1/agents/tasks` route.
- [ ] Add query params for filtering/pagination.
- [ ] Update `spec/openapi.yaml` and ensure `test_api_contract.py` passes.
- [ ] Add tests for user scoping and filters.
- [ ] Run `python -m pytest -q`.

## Notes
- Keep response payload aligned with what mobile needs (id, state, description, created_at, updated_at, optional pr_url).
- If tasks are dev-only today, it’s still useful to make listing available in dev mode (but prefer not to hardcode dev-only unless necessary).
