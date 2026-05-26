# VAI-044 Resolution

Date: 2026-05-26
Source finding: `src/handsfree/sessions.py:229`
Evidence: `/home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-044-codebase-scan-b1039b93eb48.md`

The scan evidence pointed at a broad exception handler in session validation.
Session validation should still fail closed for Redis outages and malformed
stored session hashes, but unrelated runtime errors should not be hidden by a
blanket `Exception` catch.

## Resolution

- Split Redis retrieval errors from session payload parsing.
- Replaced the broad `Exception` handler with explicit malformed session data
  handling for missing fields, invalid value types, and invalid timestamps.
- Malformed persisted session data now returns `None` and revokes the stored
  token hash so the bad record does not keep failing validation.
- Left the parseable VAI backlog metadata unchanged; the supervisor owns task
  completion state.

## Validation

- `python3 -m py_compile src/handsfree/sessions.py`
- `PYTHONPATH=$(pwd)/src python3 -m pytest -q tests/test_sessions.py::TestSessionTokenManagerEdgeCases::test_validate_session_revokes_malformed_data`
- `python3 -m ruff check src/handsfree/sessions.py tests/test_sessions.py`
