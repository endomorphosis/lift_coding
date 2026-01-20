# PR-081: Privacy mode configurable per profile

## Goal
Make privacy mode (strict / balanced / debug) configurable per user profile, instead of being hard-coded to strict.

## Context
The implementation plan explicitly calls out privacy modes (strict/balanced/debug). The backend already supports `PrivacyMode` and applies redaction, but `commands/router.py` currently hard-codes strict with a TODO.

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
