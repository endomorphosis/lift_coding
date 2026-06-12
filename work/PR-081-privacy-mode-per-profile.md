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
- The router resolves `ProfileConfig` once per request and passes its `privacy_mode` into both handler paths.
- Verified the inbox and PR summary router paths both pass `profile_config.privacy_mode` into their handlers.
- Added comprehensive tests:
  - `tests/test_profile_privacy_mode.py`: Unit tests for profile privacy mode configuration
  - `tests/test_router_privacy_mode.py`: Integration tests for router privacy mode behavior
- All 1169 tests pass successfully

## MGW-112 Resolution
- The scanner finding matched stale cleanup wording, not an open router task. Current router code reads the selected profile privacy mode before calling the inbox and PR summary handlers, and the focused profile/router privacy-mode tests cover that behavior.

## HAO-168 Resolution
- The scanner finding at line 18 was stale PR-log wording, not live router debt.
- Verified `src/handsfree/commands/router.py` uses `ProfileConfig.for_profile()`
  and passes `profile_config.privacy_mode` into inbox and PR summary handlers.
- Verified focused coverage remains in `tests/test_profile_privacy_mode.py` and
  `tests/test_router_privacy_mode.py`.
- The scanner-flagged summary line now describes completed behavior directly,
  without stale follow-up wording.

## VAI-095 Resolution
The line 18 scan finding matched a completed-work note, not unresolved product
work. The current router paths for GitHub-backed inbox and PR summaries read
`profile_config.privacy_mode` and pass that value to the existing handlers, while
all built-in profile defaults remain `PrivacyMode.STRICT`. This work log now
describes the completed router behavior without stale follow-up language that the
supervisor can re-ingest as new work.

## HAO-168 Attempt 3 Verification
- Rechecked `src/handsfree/commands/router.py`: `route()` resolves
  `ProfileConfig.for_profile(profile)` once, and the inbox plus PR summary paths
  pass `profile_config.privacy_mode` to their handlers.
- Rechecked focused coverage in `tests/test_profile_privacy_mode.py` and
  `tests/test_router_privacy_mode.py`.
- Tightened line 18 to state the completed router behavior directly.
