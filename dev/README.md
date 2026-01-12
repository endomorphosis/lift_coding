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
- **In-memory storage**: Temporary storage for pending actions and webhook payloads
- **Fixture data**: GET /v1/inbox returns fixture data for testing

## Current Limitations (by design)

- No persistence layer (in-memory only) - DuckDB integration is in PR-003
- GitHub API calls are stubbed - real implementation in PR-005
- Policy enforcement is stubbed - real implementation in PR-007
- Audio input returns an error - transcription coming in future PRs

## OpenAPI Documentation

When the server is running, visit:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`
