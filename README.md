# HandsFree Dev Companion

HandsFree Dev Companion is a voice-first GitHub workflow assistant with a Python/FastAPI backend and a React Native mobile client.

It supports command execution, confirmation-gated side effects, agent delegation, notifications, AI capability workflows, and Meta AI Glasses audio integration.

## What You Get

- Natural-language command handling through `POST /v1/command`
- Safe, policy-aware side effects (request review, rerun checks, comment, merge)
- Token-based confirmation flow for destructive/high-risk operations
- Agent task delegation, task tracking, and result retrieval
- Notification delivery APIs and subscription management
- AI capability execution endpoints and policy reporting
- Dev-friendly fixture modes plus live GitHub/OpenAI integrations

## Quick Links

- [Getting Started](GETTING_STARTED.md)
- [Documentation Index](DOCUMENTATION_INDEX.md)
- [Package Guide](docs/PACKAGE_GUIDE.md)
- [Architecture](ARCHITECTURE.md)
- [Configuration Guide](CONFIGURATION.md)
- [Configuration Reference](docs/configuration-reference.md)
- [Authentication](docs/AUTHENTICATION.md)
- [Mobile App Docs](mobile/README.md)
- [OpenAPI Spec](spec/openapi.yaml)

## Architecture Summary

System layers:

- Mobile/Device layer:
  - React Native app, native Bluetooth audio modules, Meta AI Glasses integration
- API layer:
  - FastAPI application in [src/handsfree/api.py](src/handsfree/api.py)
- Domain layer:
  - Commands, actions, agents, AI, GitHub, notifications, policy/rate-limits
- Persistence/cache layer:
  - DuckDB + optional Redis

## Backend Package Map

Core backend package: [src/handsfree](src/handsfree)

- [src/handsfree/api.py](src/handsfree/api.py): FastAPI app and endpoint handlers
- [src/handsfree/models.py](src/handsfree/models.py): shared request/response models
- [src/handsfree/auth.py](src/handsfree/auth.py): auth mode and user resolution
- [src/handsfree/commands](src/handsfree/commands): intent parsing, routing, profile behavior, pending actions
- [src/handsfree/actions](src/handsfree/actions): shared side-effect orchestration
- [src/handsfree/agents](src/handsfree/agents): delegation service, task lifecycle, result views
- [src/handsfree/github](src/handsfree/github): GitHub auth/provider/execution logic
- [src/handsfree/ai](src/handsfree/ai): AI capability execution and backend policy integration
- [src/handsfree/db](src/handsfree/db): database modules and migrations
- [src/handsfree/notifications](src/handsfree/notifications): notification delivery providers

For complete package details and runtime flows, see [docs/PACKAGE_GUIDE.md](docs/PACKAGE_GUIDE.md).

## API Surface (High-Level)

Canonical contract: [spec/openapi.yaml](spec/openapi.yaml)

Main endpoint groups:

- Commands and confirmation:
  - `/v1/command`
  - `/v1/commands/confirm`
  - `/v1/commands/action`
- Side-effect actions:
  - `/v1/actions/request-review`
  - `/v1/actions/rerun-checks`
  - `/v1/actions/comment`
  - `/v1/actions/merge`
- Agents:
  - `/v1/agents/tasks*`
  - `/v1/agents/results`
- AI:
  - `/v1/ai/*`
  - `/v1/admin/ai/*`
- Notifications:
  - `/v1/notifications*`
  - `/v1/repos/subscriptions*`
- GitHub OAuth/connections:
  - `/v1/github/oauth/*`
  - `/v1/github/connections*`
- Dev/media utilities:
  - `/v1/tts`
  - `/v1/dev/audio`
  - `/v1/dev/media`
  - `/v1/dev/peer-chat/*`

## Local Development Quick Start

### Prerequisites

- Python 3.11+
- Docker + Docker Compose
- Node.js 18+ (for mobile development)

### 1. Backend Setup

```bash
git clone https://github.com/endomorphosis/lift_coding.git
cd lift_coding
make deps
make compose-up
make dev
```

Backend runs at `http://localhost:8080`.

### 2. Basic Health Check

```bash
curl http://localhost:8080/v1/status
```

### 3. Quick Command Test (Dev Auth Mode)

```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "input": {"type": "text", "text": "show my inbox"},
    "profile": "default",
    "client_context": {
      "device": "cli",
      "locale": "en-US",
      "timezone": "UTC",
      "app_version": "0.1.0"
    }
  }'
```

### 4. Mobile App Setup

```bash
cd mobile
npm ci
npm start
```

For simulator/device workflows, use [mobile/README.md](mobile/README.md).

## Authentication Modes

Configured via `HANDSFREE_AUTH_MODE`:

- `dev`:
  - Dev-friendly mode; commonly uses `X-User-Id`
- `jwt`:
  - `Authorization: Bearer <jwt-token>`
- `api_key`:
  - `Authorization: Bearer <api-key>`

See full details in [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md).

## Configuration

Start with:

- [CONFIGURATION.md](CONFIGURATION.md) for practical setup paths
- [docs/configuration-reference.md](docs/configuration-reference.md) for exhaustive env keys

Key integrations include:

- GitHub live/fixture modes
- OpenAI TTS/STT provider selection
- Notification provider settings (APNS/FCM/WebPush/Expo)
- Agent delegation provider settings

## Agent Delegation and Runners

HandsFree can delegate tasks to external runners.

Provider selection precedence:

1. Explicit provider in request
2. `HANDSFREE_AGENT_DEFAULT_PROVIDER`
3. Auto `github_issue_dispatch` when dispatch repo + token are configured
4. Fallback provider

Runner setup docs:

- [docs/agent-runner-setup.md](docs/agent-runner-setup.md)
- [docs/AGENT_RUNNER_QUICKSTART.md](docs/AGENT_RUNNER_QUICKSTART.md)
- [docs/MINIMAL_AGENT_RUNNER.md](docs/MINIMAL_AGENT_RUNNER.md)

## Testing and Quality

Run checks from repo root:

```bash
make fmt-check
make lint
make test
make openapi-validate
```

Or run full tests directly:

```bash
.venv/bin/pytest -q
```

## Docker

### Run with Compose

```bash
docker compose up -d
docker compose logs -f api
```

### Stop

```bash
docker compose down
```

## Repository Layout

Top-level directories and key docs:

- [src](src): backend source code
- [tests](tests): test suite
- [mobile](mobile): React Native client
- [docs](docs): operational and feature docs
- [spec](spec): OpenAPI and command grammar
- [migrations](migrations): SQL migrations
- [implementation_plan](implementation_plan): design and rollout docs
- [GETTING_STARTED.md](GETTING_STARTED.md): setup guide
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md): full docs navigator

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution flow, coding standards, and testing expectations.

## License

See [LICENSE](LICENSE).
