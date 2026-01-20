# Development Guide

## Web Dev Simulator

The web dev simulator provides a user-friendly interface to test the complete handsfree loop: mic input → `/v1/command` → TTS playback.

### Quick Start

1. **Start the backend server:**
   ```bash
   make dev
   ```

2. **Open the simulator in your browser:**
   ```
   http://localhost:8080/simulator
   ```

3. **Try it out:**
   - Enter a text command (e.g., "show my inbox", "summarize pr 42")
   - Click "Send Text" to submit
   - View the parsed intent and response
   - Audio response will auto-play (if enabled in settings)

### Features

- **Text Input**: Type commands directly and submit
- **Audio Recording**: Record voice commands (requires microphone permission)
- **Audio Upload**: Upload pre-recorded audio files for testing
- **Response Display**: View parsed intents, spoken text, and UI cards
- **TTS Playback**: Automatically converts responses to speech and plays them
- **Activity Log**: Track all API interactions in real-time
- **Settings**: Configure API URL, auto-play TTS, and debug mode

### Quick Commands

The simulator includes shortcuts for common commands:
- `inbox` - Show your inbox
- `summarize pr 42` - Summarize a pull request
- `list PRs` - List your pull requests
- `agent status` - Check agent task status

### Audio Notes

- **Recording**: Uses browser's MediaRecorder API (requires HTTPS in production)
- **STT**: Audio transcription uses a stub provider by default
- **TTS**: Text-to-speech works with fixture data (no external API keys needed)
- To enable real STT/TTS providers, set environment variables (see below)

### Dev Audio Upload Endpoint

For mobile and local development, the backend provides a dev-only endpoint to upload audio bytes:

**Endpoint**: `POST /v1/dev/audio`

**Requirements**:
- Only available when `HANDSFREE_AUTH_MODE=dev`
- Requires `X-User-Id` header for authentication

**Request Body**:
```json
{
  "data_base64": "base64-encoded audio bytes",
  "format": "m4a"  // Supported: wav, m4a, mp3, opus
}
```

**Response**:
```json
{
  "uri": "file:///absolute/path/to/saved/file.m4a",
  "bytes": 12345,
  "format": "m4a",
  "user_id": "fixture-user-001"
}
```

**Usage Flow**:
1. Record or capture audio on your mobile device
2. Base64-encode the audio bytes
3. POST to `/v1/dev/audio` with the encoded data
4. Use the returned `file://` URI in subsequent `/v1/command` requests with `input.type="audio"`

**Configuration**:
- `HANDSFREE_DEV_AUDIO_DIR`: Directory for uploaded files (default: `data/dev_audio`)
- `HANDSFREE_DEV_AUDIO_MAX_BYTES`: Max file size (default: 10MB)

**Example with curl**:
```bash
# Encode an audio file
AUDIO_B64=$(base64 -w 0 recording.m4a)

# Upload to dev endpoint
curl -X POST http://localhost:8080/v1/dev/audio \
  -H "Content-Type: application/json" \
  -H "X-User-Id: fixture-user-001" \
  -d "{\"data_base64\": \"$AUDIO_B64\", \"format\": \"m4a\"}"

# Use the returned URI in a command request
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -H "X-User-Id: fixture-user-001" \
  -d '{"input": {"type": "audio", "uri": "file:///path/from/previous/response.m4a"}}'
```

**Security Notes**:
- This endpoint is **only** for development and testing
- Uploaded files are stored locally on the server
- No cleanup/retention policy is currently enforced (files persist until manually deleted)
- Do not use this endpoint in production environments

### Troubleshooting

- **CORS errors**: The simulator is served from the same origin as the API, so CORS should not be an issue
- **Microphone not working**: Ensure you've granted browser permission and are using HTTPS (or localhost)
- **Audio not playing**: Check browser audio permissions and volume settings

## Running the Backend Server

The backend API server runs on `http://localhost:8080` by default.

### Start the server

```bash
make dev
```

This will start the FastAPI server with auto-reload enabled for development.

## Push Notifications Demo (Expo)

This repo supports Expo push delivery via notification subscriptions (`platform=expo`).

**Server configuration**

- Set `HANDSFREE_EXPO_MODE=real` to actually send push tickets to Expo.
- Ensure `HANDSFREE_NOTIFICATION_PROVIDER` is **not** set to `logger`/`dev` (that overrides platform-specific providers).
- Optional: set `HANDSFREE_EXPO_ACCESS_TOKEN` for higher rate limits.

Example:

```bash
export HANDSFREE_AUTH_MODE=dev
export HANDSFREE_EXPO_MODE=real
unset HANDSFREE_NOTIFICATION_PROVIDER
make dev
```

**Device setup (mobile app)**

1) In the mobile app, point the base URL at your backend (must be reachable from the phone).
2) Go to the **Status** tab → **Enable Push**.
3) In the same screen, add a **Repo Subscription** for a repo you’ll replay webhooks for (e.g. `endomorphosis/lift_coding`).

**Trigger a notification (webhook replay)**

Option A (phone-only):

- In the mobile app → **Status** → **Repo Subscriptions** → **Send Test Webhook (PR Opened)**

Option B (CLI):

From this repo root, replay a webhook fixture into your running backend:

```bash
/home/barberb/lift_coding/.venv/bin/python dev/replay_webhook.py \
  tests/fixtures/github/webhooks/pull_request.opened.json
```

If you have push enabled and are subscribed to that repo, you should receive a push; when the app is foregrounded it will speak the message via TTS.

### Install dependencies

First time setup:

```bash
make deps
pip install -e .
```

## Running in Live GitHub Mode

By default, the backend uses fixture data for GitHub API calls. To enable live GitHub API integration, you can use either a personal access token or GitHub App authentication.

### Option 1: Personal Access Token (Simple, for development)

Set environment variables before starting the server:

```bash
export GITHUB_TOKEN=ghp_YOUR_PERSONAL_ACCESS_TOKEN_HERE
make dev
```

**Note:** Setting `GITHUB_TOKEN` alone is sufficient to enable live mode. The `GITHUB_LIVE_MODE` environment variable is optional and only used by legacy authentication providers.

#### Get a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token (classic) with these scopes:
   - `repo` - Full control of private repositories
   - `read:org` - Read org and team membership
3. Copy the token and use it as `GITHUB_TOKEN`

### Option 2: GitHub App (Recommended for production)

For production use, GitHub App authentication is recommended as it provides better security and per-installation access control.

Set these environment variables:

```bash
export GITHUB_APP_ID=123456
export GITHUB_APP_PRIVATE_KEY_PEM="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"
export GITHUB_INSTALLATION_ID=78901234
make dev
```

**Note:** The private key can include actual newlines or escaped newlines (`\n`). Both formats are supported.

#### Create a GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App
2. Set up your app with these permissions:
   - Repository permissions:
     - Contents: Read
     - Pull requests: Read & Write
     - Issues: Read & Write
   - Subscribe to events as needed
3. Generate a private key (RSA format) and download it
4. Install the app on your organization/repository
5. Note the App ID and Installation ID from the app settings

**Security notes:**
- Private keys are never logged or stored in the database
- Installation tokens are cached in memory only
- Tokens are automatically refreshed before expiry (default: 5 minutes before expiration)
- JWT tokens expire after 10 minutes (GitHub's maximum)

### Configuration Priority

When multiple authentication methods are configured, the system uses this priority order:

1. **GitHub App** (if `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY_PEM`, and `GITHUB_INSTALLATION_ID` are set)
2. **Personal Access Token** (if `GITHUB_TOKEN` is set)
3. **Fixture-only mode** (default, uses test fixtures)

### Configuration Details

- **`GITHUB_APP_ID`**: Your GitHub App ID (numeric)
- **`GITHUB_APP_PRIVATE_KEY_PEM`**: Your GitHub App private key in PEM format (supports escaped newlines)
- **`GITHUB_INSTALLATION_ID`**: The installation ID for your GitHub App
- **`GITHUB_TOKEN`**: Your GitHub personal access token (for simple auth) - setting this alone enables live mode
- **`GITHUB_LIVE_MODE`**: Optional, legacy setting; set to `true`, `1`, or `yes` (only used by legacy auth providers)
- **`HANDS_FREE_GITHUB_MODE`**: Set to `fixtures` to force fixture mode even when tokens are configured
- When no authentication is configured, the system uses fixture data (default behavior)

### User Identity in Live Mode

When making API calls in live mode, the system uses the `X-User-Id` header to associate requests with users.

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

GitHub connection metadata (installation IDs, token references, scopes) is stored in the database. Raw tokens are **never** stored in the database. Tokens are managed in memory with automatic refresh.

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
- By default, GitHub data may come from fixtures unless live mode is enabled/configured
- GitHub App installation UI and OAuth redirects are out of scope for now
- Audio input returns an error - transcription coming in future PRs

### GitHub fixtures vs live mode

The dev stack supports both fixture mode (safe, deterministic) and live GitHub API calls.

- **Fixture mode** (default when no token is configured): the GitHub provider falls back to fixture data.
- **Live mode**: provide `GITHUB_TOKEN` or GitHub App credentials to enable real GitHub API calls.
- **Force fixtures**: set `HANDS_FREE_GITHUB_MODE=fixtures` to force fixture mode even if tokens are configured.

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

