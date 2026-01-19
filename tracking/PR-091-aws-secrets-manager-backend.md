# PR-091: AWS Secrets Manager backend for secret storage

## Goal
Implement an AWS Secrets Manager-backed `SecretManager` so production deployments can persist OAuth tokens / API secrets outside process env vars.

## Context
`src/handsfree/secrets/factory.py` advertises `SECRET_MANAGER_TYPE=aws` but currently raises `NotImplementedError`. Docs in `docs/SECRET_STORAGE_AND_SESSIONS.md` also list “AWS Secrets Manager (coming soon)”.

We already support:
- `env` (development)
- `vault` (production)

AWS Secrets Manager support unblocks a common deployment path without requiring Vault.

## Scope
- Add `AWSSecretManager` implementation (new file suggested: `src/handsfree/secrets/aws_secrets.py`).
- Wire it into `src/handsfree/secrets/factory.py` for `SECRET_MANAGER_TYPE=aws`.
- Support the full `SecretManager` interface:
  - `store_secret`, `get_secret`, `update_secret`, `delete_secret`, `list_secrets`
- Add minimal documentation updates:
  - Update `docs/SECRET_STORAGE_AND_SESSIONS.md` to describe AWS setup and remove “coming soon”.

## Configuration
Suggested env vars (feel free to adjust if existing conventions differ):
- `SECRET_MANAGER_TYPE=aws`
- `AWS_REGION` (or `AWS_DEFAULT_REGION`)
- `HANDSFREE_AWS_SECRETS_PREFIX` (optional; namespace secrets, e.g. `handsfree/`)

Auth should use standard AWS credential resolution (env vars / IAM role / IRSA).

## Non-goals
- Automatic secret rotation.
- Supporting every AWS partition nuance; just standard boto3.

## Acceptance criteria
- Setting `SECRET_MANAGER_TYPE=aws` no longer raises `NotImplementedError`.
- Storing a secret returns a stable reference (e.g. `aws://<secret_id>`).
- `get_secret(reference)` returns the stored value.
- `update_secret` updates the value.
- `delete_secret` removes the secret.
- `list_secrets(prefix=...)` returns references for secrets within the namespace.

## Suggested files
- `src/handsfree/secrets/aws_secrets.py` (new)
- `src/handsfree/secrets/factory.py`
- `docs/SECRET_STORAGE_AND_SESSIONS.md`
- Dependency management (`pyproject.toml` or requirements) for `boto3` if needed

## Validation
- Add unit tests (preferred) OR a small manual snippet in docs verifying store/get/update/delete.
