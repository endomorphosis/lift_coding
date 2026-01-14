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

## Text-to-Speech (TTS) Integration

The API includes a `/v1/tts` endpoint for converting text to speech. This is useful for the hands-free dev loop.

### Basic TTS usage

Convert any text to speech:

```bash
curl -s http://localhost:8080/v1/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello world","format":"wav"}' \
  --output speech.wav
```

### TTS Demo Script

Use the included demo script to see the full dev loop in action:

```bash
# Convert a command response to speech
python dev/tts_demo.py "inbox"

# Convert PR summary to speech
python dev/tts_demo.py "summarize pr 123"

# Convert custom text to speech
python dev/tts_demo.py --text "This is a custom message"

# Play audio automatically (requires audio player)
python dev/tts_demo.py "inbox" --play

# Use MP3 format instead of WAV
python dev/tts_demo.py "inbox" --format mp3 --output /tmp/inbox.mp3
```

The demo script demonstrates:
1. Submitting a command to `/v1/command`
2. Extracting the `spoken_text` from the response
3. Calling `/v1/tts` to convert it to audio
4. Saving the audio file locally (and optionally playing it)

### TTS API Details

**Endpoint:** `POST /v1/tts`

**Request body:**
```json
{
  "text": "Text to convert to speech",
  "voice": "en-US-male",  // Optional
  "format": "wav"          // wav or mp3, default: wav
}
```

**Response:**
- Content-Type: `audio/wav` or `audio/mpeg`
- Body: Binary audio data

**Validation:**
- Text must not be empty
- Text maximum length: 5000 characters

**Implementation:**
- Uses stub/fixture provider by default (returns deterministic audio)
- Real TTS providers can be enabled via environment variables in production
- No secrets required for fixture mode

