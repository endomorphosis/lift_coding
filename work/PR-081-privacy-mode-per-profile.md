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
- Verified the inbox and PR summary router paths both pass `profile_config.privacy_mode` into their handlers.
- Added comprehensive tests:
  - `tests/test_profile_privacy_mode.py`: Unit tests for profile privacy mode configuration
  - `tests/test_router_privacy_mode.py`: Integration tests for router privacy mode behavior
- All 1169 tests pass successfully

## MGW-112 Resolution
- The scanner finding matched stale cleanup wording, not an open router task. Current router code reads the selected profile privacy mode before calling the inbox and PR summary handlers, and the focused profile/router privacy-mode tests cover that behavior.
