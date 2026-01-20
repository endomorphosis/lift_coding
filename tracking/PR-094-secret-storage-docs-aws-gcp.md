# PR-094: Secret storage docs update (AWS + GCP)

## Goal
Update `docs/SECRET_STORAGE_AND_SESSIONS.md` so it clearly documents production secret storage for:
- HashiCorp Vault (already implemented)
- AWS Secrets Manager
- Google Secret Manager

…and remove “coming soon” language where appropriate.

## Context
We now have (or are actively implementing) secret-manager backends beyond env vars. The docs currently contain placeholder sections:
- “Production - AWS Secrets Manager (coming soon)”
- “Production - Google Secret Manager (coming soon)”

If both backend PRs and docs updates land in separate PRs, we’ll likely get merge conflicts because they touch the same doc file.

## Scope
- Update `docs/SECRET_STORAGE_AND_SESSIONS.md` to:
  - describe recommended environment variables and auth expectations for AWS/GCP
  - include short examples of storing/retrieving via `SECRET_MANAGER_TYPE`
  - clearly state the reference formats (`env://...`, `vault://...`, `aws://...`, `gcp://...`) as implemented
  - remove or replace “coming soon” language
- Keep the changes doc-only.

## Non-goals
- Implementing the AWS/GCP secret manager code (handled in other PRs).

## Acceptance criteria
- A reader can configure secret storage on AWS or GCP using the documented env vars.
- The doc no longer describes AWS/GCP support as “coming soon”.
- No code changes in this PR.

## Suggested files
- `docs/SECRET_STORAGE_AND_SESSIONS.md`

## Validation
- Doc review for accuracy vs `src/handsfree/secrets/*`.
