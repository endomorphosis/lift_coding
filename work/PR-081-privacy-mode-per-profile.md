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
- Removed TODO comments in router.py (lines 504 and 669)
- Added comprehensive tests:
  - `tests/test_profile_privacy_mode.py`: Unit tests for profile privacy mode configuration
  - `tests/test_router_privacy_mode.py`: Integration tests for router privacy mode behavior
- All 1169 tests pass successfully
