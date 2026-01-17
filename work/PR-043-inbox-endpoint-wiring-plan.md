# PR-043: Wire `GET /v1/inbox` to inbox handler

## Status
Queued for Copilot agent implementation.

## Goal
Make `GET /v1/inbox` return the same rich, profile-aware items as the `inbox.list` intent path, instead of `_get_fixture_inbox_items()`.

## Checklist
- [ ] Replace fixture stub in `GET /v1/inbox`
- [ ] Use `ProfileConfig` for filtering
- [ ] Keep deterministic fixture behavior as fallback
- [ ] Update/extend tests in `tests/test_api_contract.py`
