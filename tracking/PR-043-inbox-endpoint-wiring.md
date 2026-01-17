# PR-043: Wire `GET /v1/inbox` to real inbox handler

## Goal
Replace the fixture-only implementation of `GET /v1/inbox` with the same handler logic used for `inbox.list` (cards + checks summary + profile-aware filtering).

## Current Problem
In `src/handsfree/api.py`, `GET /v1/inbox` currently returns `_get_fixture_inbox_items()` and only applies a tiny workout-only filter.

This is inconsistent with:
- `handle_inbox_list()` (which produces richer items + summaries)
- The intent path for `inbox.list` (which already uses handler conversion)

## Scope
- Update `GET /v1/inbox` to:
  - Use `ProfileConfig.for_profile(profile)` for filtering/truncation
  - Use `handle_inbox_list(provider=_github_provider, ...)` to produce items
  - Convert handler items into `InboxResponse` (same item shape as today)
- Keep fixture-backed default behavior for deterministic tests.

## Design Choices
User identity for now:
- In fixture mode: continue using a stable fixture username (e.g., `"testuser"`).
- In live mode (future or optional here): accept `user_id: CurrentUser` and use `user_id` for auth; GitHub username may still be needed depending on provider behavior.

## Acceptance Criteria
- Existing tests for `GET /v1/inbox` remain green or are updated to match richer output.
- `GET /v1/inbox?profile=workout` respects profile-based filtering.

## Files
- `src/handsfree/api.py`
- `src/handsfree/handlers/inbox.py`
- `tests/test_api_contract.py`
