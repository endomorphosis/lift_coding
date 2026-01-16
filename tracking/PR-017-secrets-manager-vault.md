# PR-017: Add Vault-backed SecretManager (production-ready secrets)

## Goal
Implement a non-env secret backend so GitHub App keys, tokens, and push keys do not require plaintext environment variables in production.

## Background
The plan calls for production secrets handling. The repo currently supports `EnvSecretManager` only; other backends are `NotImplementedError`.

## Scope
- Implement `VaultSecretManager` using HashiCorp Vault.
- Wire it into `get_secret_manager()` behind `SECRET_MANAGER_TYPE=vault`.
- Add documentation for required env vars and expected secret formats.
- Add tests with mocks.

## Non-goals
- KMS encryption at rest.
- Full secrets rotation automation.

## Acceptance criteria
- Setting `SECRET_MANAGER_TYPE=vault` uses the new manager.
- Secrets can be read/written and referenced via a stable `vault://...` ref format.
- Missing configuration fails fast with clear error messages.
- Unit tests cover read/write/list and common error conditions.

## Config (proposed)
- `VAULT_ADDR`
- `VAULT_TOKEN` (dev) or `VAULT_ROLE_ID`/`VAULT_SECRET_ID` (AppRole)
- `VAULT_MOUNT` (default `secret`)

