# VAI-088 Codebase Scan Finding

Date: 2026-05-27
Fingerprint: d0d2e565dde4990f1c8522d8a02b906229127e6c
Kind: annotated_followup
Source: tracking/PR-081-privacy-mode-per-profile.md:7
Priority: P3
Track: docs

## Evidence

```text
The implementation plan explicitly calls out privacy modes (strict/balanced/debug). The backend already supports `PrivacyMode` and applies redaction, but `commands/router.py` currently hard-codes strict with a TODO.
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Resolved as a stale tracking annotation on 2026-05-27. Current code already
implements the requested behavior: `ProfileConfig` defines `privacy_mode`,
built-in profiles default to `PrivacyMode.STRICT`, and `CommandRouter` forwards
`profile_config.privacy_mode` to both `handle_inbox_list()` and
`handle_pr_summarize()`. Focused coverage exists in
`tests/test_profile_privacy_mode.py` and `tests/test_router_privacy_mode.py`.
Updated `tracking/PR-081-privacy-mode-per-profile.md` so the supervisor does
not treat the old hard-coded-strict note as an active finding.
