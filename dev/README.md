# Development Guide

## Running the Backend Server

The backend API server runs on `http://localhost:8080` by default.

### Start the server

```bash
make dev
```

This will start the FastAPI server with auto-reload enabled for development.

### Install dependencies

First time setup:

```bash
make deps
pip install -e .
```

## Running in Live GitHub Mode

By default, the backend uses fixture data for GitHub API calls. To enable live GitHub API integration:

### Enable Live Mode

Set environment variables before starting the server:

```bash
export GITHUB_TOKEN=ghp_YOUR_PERSONAL_ACCESS_TOKEN_HERE
export GITHUB_LIVE_MODE=true
make dev
```

### Get a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token (classic) with these scopes:
   - `repo` - Full control of private repositories
   - `read:org` - Read org and team membership
3. Copy the token and use it as `GITHUB_TOKEN`

### Configuration Details

- **`GITHUB_TOKEN`**: Your GitHub personal access token
- **`GITHUB_LIVE_MODE`**: Set to `true`, `1`, or `yes` to enable live mode
- When both are set, API calls will use the real GitHub API
- When not set or disabled, the system uses fixture data (default behavior)

### User Identity in Live Mode

When making API calls in live mode, the system uses the `X-User-Id` header to associate requests with users. The token provider reads from `GITHUB_TOKEN` regardless of user ID (for now).

```bash
curl -s http://localhost:8080/v1/command \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 12345678-1234-1234-1234-123456789012' \
  -d '{
    "input": {"type":"text","text":"inbox"},
    "profile":"default",
    "client_context":{"device":"simulator"},
    "idempotency_key":"dev-1"
  }' | jq
```

### Connection Metadata

GitHub connection metadata (installation IDs, token references, scopes) is stored in the database. Raw tokens are **never** stored in the database.

Create a connection:

```bash
curl -s http://localhost:8080/v1/github/connections \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 12345678-1234-1234-1234-123456789012' \
  -d '{
    "installation_id": 12345,
    "token_ref": "secret://tokens/github/user123",
    "scopes": "repo,read:org"
  }' | jq
```

List connections:

```bash
curl -s http://localhost:8080/v1/github/connections \
  -H 'X-User-Id: 12345678-1234-1234-1234-123456789012' | jq
```

## Testing the API

### Run all tests

```bash
make test
```

### Run specific test file

```bash
python3 -m pytest tests/test_api_contract.py -v
```

### Manual testing with curl

See `implementation_plan/dev/simulator_cli.md` for example curl commands.

#### Test inbox command

```bash
curl -s http://localhost:8080/v1/command \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {"type":"text","text":"inbox"},
    "profile":"workout",
    "client_context":{"device":"simulator","locale":"en-US","timezone":"America/Los_Angeles","app_version":"0.1.0","noise_mode":true},
    "idempotency_key":"dev-1"
  }' | jq
```

#### Test PR summarize command

```bash
curl -s http://localhost:8080/v1/command \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {"type":"text","text":"summarize pr 412"},
    "profile":"default",
    "client_context":{"device":"simulator","locale":"en-US","timezone":"America/Los_Angeles","app_version":"0.1.0"},
    "idempotency_key":"dev-2"
  }' | jq
```

#### Test confirmation

First get a pending action token from the previous command, then:

```bash
curl -s http://localhost:8080/v1/commands/confirm \
  -H 'Content-Type: application/json' \
  -d '{"token":"<PENDING_ACTION_TOKEN>","idempotency_key":"dev-confirm-1"}' | jq
```

## CI Checks

Run all CI checks before committing:

```bash
make fmt-check lint test openapi-validate
```

Or fix formatting automatically:

```bash
make fmt
make lint
```

## Architecture

- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **Pydantic**: Schema validation aligned with `spec/openapi.yaml`
- **DuckDB**: Embedded database for persistence
- **Fixture data**: Used by default for GitHub API calls (live mode optional)

## Current Limitations (by design)

- Live GitHub mode uses a single `GITHUB_TOKEN` for all users (per-user tokens in future PRs)
- Real GitHub API calls are planned but not yet implemented (falls back to fixtures)
- GitHub App installation UI and OAuth redirects are out of scope for now
- Audio input returns an error - transcription coming in future PRs

## OpenAPI Documentation

When the server is running, visit:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`
