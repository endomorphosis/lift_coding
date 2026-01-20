# PR-073: Policy configuration file (MVP3)

## Goal
Move policy rules (repo allowlists, action-specific rules) out of hardcoded defaults and into a configuration file so the demo/prod policy can be adjusted without code changes.

## Context
The backend policy engine is already implemented and working for the demo, but policy configuration is currently largely code-driven. We want a config-driven source of truth with safe defaults.

## Scope
- Add a new config file (suggested: `config/policies.yaml`) that defines policy rules.
- Load policy rules from this file at backend startup.
- Support (at minimum):
  - per-action policy: `ALLOW` | `REQUIRE_CONFIRMATION` | `DENY`
  - per-repo overrides using `owner/repo` full names
  - a reasonable default/fallback policy when the file is missing or invalid
- Optional (nice-to-have): allow reload without restart (signal, endpoint, or file mtime polling).

## Non-goals
- Building a full policy admin UI.
- Complex rule language (regex, conditions, etc.). Keep it simple and explicit.

## Acceptance criteria
- Policies are configurable without code changes by editing `config/policies.yaml`.
- Supports per-repo and per-action rules.
- If the config file is missing/invalid, the backend still starts and uses safe defaults.
- Unit tests cover parsing + application of at least:
  - default policy
  - repo override
  - invalid YAML handling

## Implementation notes
- Prefer a strict schema with clear error messages.
- Avoid changing existing policy semantics unless explicitly required; preserve current behavior as the default config.

## Suggested files
- `src/handsfree/policy.py` (or the module that currently owns policy evaluation)
- `src/handsfree/config.py` (if a config loader exists)
- `config/policies.yaml` (new)
- Tests under `tests/` (new or extend existing policy tests)

## Validation
- Run `python -m pytest -q`.

