# PR-092: Google Secret Manager backend for secret storage

## Goal
Implement a Google Secret Manager-backed `SecretManager` so production deployments on GCP can persist OAuth tokens / API secrets outside process env vars.

## Context
`src/handsfree/secrets/factory.py` advertises `SECRET_MANAGER_TYPE=gcp` but currently raises `NotImplementedError`. Docs in `docs/SECRET_STORAGE_AND_SESSIONS.md` also list “Google Secret Manager (coming soon)”.

We already support:
- `env` (development)
- `vault` (production)

## Scope
- Add `GCPSecretManager` implementation (suggested new file: `src/handsfree/secrets/gcp_secrets.py`).
- Wire it into `src/handsfree/secrets/factory.py` for `SECRET_MANAGER_TYPE=gcp`.
- Support the full `SecretManager` interface:
  - `store_secret`, `get_secret`, `update_secret`, `delete_secret`, `list_secrets`
- Update `docs/SECRET_STORAGE_AND_SESSIONS.md` to document GCP setup and remove “coming soon”.

## Configuration
Suggested env vars:
- `SECRET_MANAGER_TYPE=gcp`
- `GOOGLE_CLOUD_PROJECT` (or `GCP_PROJECT_ID`)
- `HANDSFREE_GCP_SECRETS_PREFIX` (optional namespace)

Auth should use standard Google ADC (service account / workload identity).

## Non-goals
- Automatic secret rotation.
- Supporting every IAM permutation; just standard client usage.

## Acceptance criteria
- Setting `SECRET_MANAGER_TYPE=gcp` no longer raises `NotImplementedError`.
- Storing a secret returns a stable reference (e.g. `gcp://projects/<project>/secrets/<name>` or `gcp://<secret_name>`).
- `get_secret(reference)` returns the stored value.
- `update_secret` updates the value (usually via a new version).
- `delete_secret` removes the secret.
- `list_secrets(prefix=...)` returns references for secrets within the namespace.

## Suggested files
- `src/handsfree/secrets/gcp_secrets.py` (new)
- `src/handsfree/secrets/factory.py`
- `docs/SECRET_STORAGE_AND_SESSIONS.md`
- Dependency management for `google-cloud-secret-manager` if needed

## Validation
- Add unit tests (preferred) OR a small manual snippet in docs verifying store/get/update/delete.
