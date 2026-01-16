# PR-023: GitHub OAuth auth flow (backend)

## Goal
Implement a minimal GitHub OAuth flow so the backend can obtain a user-scoped token without requiring manual PAT entry.

## Background
The repo already supports storing tokens securely via the configured `SecretManager` and creating GitHub connection records. What’s missing is the OAuth handshake endpoints (start/callback) and token exchange.

## Scope
- Add OAuth “start” endpoint that redirects users to GitHub’s OAuth authorize URL.
- Add OAuth “callback” endpoint that exchanges `code` for an access token.
- Store the resulting token using the existing `SecretManager` and create/update a GitHub connection row.
- Add configuration via env vars (documented in this PR):
  - `GITHUB_OAUTH_CLIENT_ID`
  - `GITHUB_OAUTH_CLIENT_SECRET`
  - `GITHUB_OAUTH_REDIRECT_URI`
  - optional: `GITHUB_OAUTH_SCOPES`
- Add tests where practical (e.g., using httpx mocking) to validate:
  - correct redirect URL shape
  - token exchange call
  - token storage + connection persistence

## Non-goals
- Mobile/web client UI implementation.
- Supporting every OAuth edge case (advanced state mgmt, PKCE) unless already needed.

## Acceptance criteria
- OAuth start/callback endpoints exist and are OpenAPI-documented.
- Successful callback stores token securely and creates a GitHub connection for the authenticated user.
- Errors are handled safely (no token leaks in logs).
- Tests remain green.

## Notes / Pointers
- Existing connection endpoints: `src/handsfree/api.py` (`/v1/github/connections`)
- Secrets: `src/handsfree/secrets/*`
- GitHub HTTP client utilities: `src/handsfree/github/*`
