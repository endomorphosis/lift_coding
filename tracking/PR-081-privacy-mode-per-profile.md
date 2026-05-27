# PR-081: Privacy mode configurable per profile

## Goal
Document the landed change that makes privacy mode (strict / balanced / debug) configurable per user profile, with `strict` remaining the default.

## Context
The implementation plan explicitly calls out privacy modes (strict/balanced/debug). This PR has landed: `ProfileConfig` now carries `privacy_mode`, built-in profiles default to `PrivacyMode.STRICT`, and `commands/router.py` passes `profile_config.privacy_mode` into the inbox and PR summary handlers.

## Scope
- Add profile-level privacy mode selection.
  - Source of truth should be profile configuration (existing profile system) rather than per-request hacks.
  - Default remains `strict`.
- Ensure the selected privacy mode is consistently applied to:
  - inbox summaries
  - PR summaries
  - debug information returned in `CommandResponse`
- Add tests to validate that different profiles produce appropriately redacted output.

## Non-goals
- Mobile UI changes (profile selector UI is tracked separately).
- Changing the meaning of strict/balanced/debug.

## Acceptance criteria
- Profiles can specify privacy mode and it takes effect end-to-end.
- Default profile continues to behave as today (`strict`).
- Tests cover at least:
  - strict mode redaction
  - balanced mode includes limited excerpts
  - debug mode includes debug fields

## Suggested files
- `src/handsfree/commands/router.py`
- Profile config source (where profiles are defined/loaded)
- `src/handsfree/handlers/inbox.py`
- `src/handsfree/handlers/pr_summary.py`
- Tests under `tests/`

## Validation
- Run `python -m pytest -q`.

## References
- `src/handsfree/commands/profiles.py` - profile-level `privacy_mode` source of truth.
- `src/handsfree/commands/router.py` - router passes the profile privacy mode to summary handlers.
- `tests/test_profile_privacy_mode.py` - profile privacy mode coverage.
- `tests/test_router_privacy_mode.py` - router privacy mode coverage.
- `work/PR-081-privacy-mode-per-profile.md` - implementation work log.

## Resolution notes
The prior context line was stale. For GitHub-backed inbox and PR summary paths,
the router reads the selected profile configuration and forwards that mode to
the existing redaction handlers.
