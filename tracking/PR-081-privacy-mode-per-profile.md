# PR-081: Privacy mode configurable per profile

## Goal
Document and maintain the landed profile-level privacy mode behavior: strict /
balanced / debug are selected through profile configuration, `strict` remains
the default, and router-selected profiles drive redaction behavior.

## Context
The implementation plan explicitly calls out privacy modes
(strict/balanced/debug). PR-081 is implemented in the backend: `ProfileConfig`
includes a `privacy_mode` field, built-in profiles default to
`PrivacyMode.STRICT` for safety, and `CommandRouter` passes
`profile_config.privacy_mode` into the inbox and PR summary handlers. Keep this
tracker aligned with that shipped behavior so stale implementation notes do not
get re-ingested as new work.

## Scope
- Maintain profile-level privacy mode selection.
  - Source of truth should be profile configuration (existing profile system) rather than per-request hacks.
  - Default remains `strict`.
- Ensure the selected privacy mode is consistently applied to:
  - inbox summaries
  - PR summaries
  - debug information returned in `CommandResponse`
- Maintain tests validating that different profiles produce appropriately redacted output.

## Non-goals
- Mobile UI changes (profile selector UI is tracked separately).
- Changing the meaning of strict/balanced/debug.

## Acceptance criteria
- Profiles can specify privacy mode through `ProfileConfig` and it takes effect in router handler calls.
- Default profile continues to behave as today (`strict`).
- Tests cover at least:
  - strict mode redaction
  - balanced mode includes limited excerpts
  - debug mode includes debug fields

## References
- `src/handsfree/commands/profiles.py` - profile-level `privacy_mode` configuration.
- `src/handsfree/commands/router.py` - passes selected profile privacy mode to handlers.
- `src/handsfree/handlers/inbox.py` - applies privacy mode to inbox summaries and debug fields.
- `src/handsfree/handlers/pr_summary.py` - applies privacy mode to PR descriptions and debug fields.
- `tests/test_profile_privacy_mode.py` - focused profile configuration coverage.
- `tests/test_router_privacy_mode.py` - focused router privacy-mode coverage.
- `tests/test_inbox.py` - strict, balanced, debug inbox redaction coverage.
- `tests/test_pr_summary.py` - strict, balanced, debug PR summary coverage.
- `work/PR-081-privacy-mode-per-profile.md` - implementation work log.

## Resolution notes
The earlier scanner finding matched stale context that still described the
router as strict-only. For GitHub-backed inbox and PR summary paths, the router
now reads the selected profile configuration and forwards that mode to the
existing redaction handlers. This tracker now points at the shipped
implementation instead of repeating the obsolete annotation.

## Validation
- Run `python -m pytest -q`.
