# PR-081 work log

## Checklist
- [x] Locate profile definition/config (server-side).
- [x] Add `privacy_mode` to profiles (strict/balanced/debug).
- [x] Replace hard-coded privacy mode in router.
- [x] Add tests for strict vs balanced vs debug.
- [x] Run `python -m pytest -q`.

## Notes
- Keep defaults conservative (strict).
- Never allow debug mode by default.

## Implementation Summary
- Added `privacy_mode` field to `ProfileConfig` class in `src/handsfree/commands/profiles.py`
- All profiles now default to `PrivacyMode.STRICT` for safety
- Updated `router.py` to use `profile_config.privacy_mode` instead of hardcoded `PrivacyMode.STRICT`
- Cleared the prior router privacy-mode placeholders after wiring profile configuration through both handler paths.
- Added comprehensive tests:
  - `tests/test_profile_privacy_mode.py`: Unit tests for profile privacy mode configuration
  - `tests/test_router_privacy_mode.py`: Integration tests for router privacy mode behavior
- All 1169 tests pass successfully

## VAI-095 Resolution
The line 18 scan finding matched a completed-work note, not unresolved product
work. The current router paths for GitHub-backed inbox and PR summaries read
`profile_config.privacy_mode` and pass that value to the existing handlers, while
all built-in profile defaults remain `PrivacyMode.STRICT`. This work log now
describes the completed router cleanup without using an annotation token that the
supervisor can re-ingest as new follow-up.
