# Handsfree Dev Companion

A proof-of-concept AI companion for GitHub that helps manage pull requests, issues, and code reviews using fixture-based development and safe policy-driven automation.

## Stack

- **DuckDB** (embedded) for persistence
- **Redis** for caching and job queues
- **Python 3.11+** with FastAPI (backend server added in PR-002)

## Agent Delegation

Handsfree can delegate tasks to external agent runners that monitor a dispatch repository and perform work:

- **Dispatch**: Create GitHub issues in a dedicated dispatch repository with task metadata
- **Agent Runners**: External processes (GitHub Actions, Copilot, custom runners) monitor and process tasks
- **Correlation**: PRs created by agents automatically correlate back to tasks via webhook tracking
- **Notifications**: Task lifecycle events emit notifications (created, running, completed)

### Provider Selection

When delegating tasks without specifying a provider, the system automatically selects the best available provider:

1. **Explicit provider** - Always honored if specified in the API call
2. **`HANDSFREE_AGENT_DEFAULT_PROVIDER`** - Environment variable override
3. **`github_issue_dispatch`** - Automatically selected when `HANDSFREE_AGENT_DISPATCH_REPO` + `GITHUB_TOKEN` are configured
4. **`copilot`** - Fallback when no other provider is configured

This means you can configure `github_issue_dispatch` once via environment variables, and all agent delegation will automatically use real GitHub issue dispatch without needing to specify the provider in every API call.

See the [Agent Runner Setup Guide](docs/agent-runner-setup.md) for configuration instructions.

## Quick Demo

Want to quickly test the API? Use the demo environment configuration and smoke test:

1. **Copy the demo environment template**
   ```bash
   cp .env.example.demo .env
   ```

2. **Start the server**
   ```bash
   make dev
   ```

3. **Run the smoke test** (in a separate terminal)
   ```bash
   python scripts/smoke_demo.py
   ```

The smoke test validates that the server is running correctly by checking:
- `/v1/status` - Service health and dependencies
- `/v1/tts` - Text-to-speech endpoint
- `/v1/command` - Command processing with a simple inbox query
- `/v1/notifications` - Notification listing (non-fatal if not configured)

The script exits with code 0 on success, non-zero on failure, and prints actionable errors for any issues.

**Note:** The demo configuration uses fixture-based responses and doesn't require external services like GitHub or Redis.

## Quickstart

### Prerequisites

- Python 3.11 or later
- Docker & Docker Compose
- Git

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/endomorphosis/lift_coding.git
   cd lift_coding
   ```

2. **Install dependencies**
   ```bash
   make deps
   ```

3. **Start Docker services** (Redis)
   ```bash
   make compose-up
   ```

4. **Run tests**
   ```bash
   make test
   ```

5. **Stop Docker services** when done
   ```bash
   make compose-down
   ```

## Docker Deployment

### Running with Docker Compose

The easiest way to run the entire stack (API + Redis) is using Docker Compose:

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f api

# Stop all services
docker compose down
```

The API will be available at `http://localhost:8080`.

### Building the Docker Image

To build the Docker image manually:

```bash
docker build -t handsfree-api .
```

### Running the Docker Container

Run the API container with environment variables:

```bash
docker run -d \
  --name handsfree-api \
  -p 8080:8080 \
  -e HANDSFREE_AUTH_MODE=dev \
  -e REDIS_HOST=redis \
  -e REDIS_ENABLED=true \
  -v handsfree-data:/app/data \
  handsfree-api
```

### Environment Variables

Configure the containerized API using these environment variables:

**Quick start:** Copy `.env.example` to `.env` and customize the values for your environment.

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Port for the API server |
| `HANDSFREE_AUTH_MODE` | `dev` | Authentication mode: `dev`, `jwt`, or `api_key` |
| `DUCKDB_PATH` | `/app/data/handsfree.db` | Path to DuckDB database file |
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_ENABLED` | `true` | Enable/disable Redis caching |
| `HANDSFREE_ENABLE_METRICS` | `false` | Enable metrics endpoint at `/v1/metrics` |
| `GITHUB_TOKEN` | - | GitHub personal access token (optional) |
| `GITHUB_LIVE_MODE` | `false` | Enable live GitHub API mode |
| `GITHUB_APP_ID` | - | GitHub App ID (optional) |
| `GITHUB_APP_PRIVATE_KEY_PEM` | - | GitHub App private key (optional) |
| `GITHUB_INSTALLATION_ID` | - | GitHub App installation ID (optional) |

### Authentication

HandsFree Dev Companion supports three authentication modes:

#### Development Mode (default)
```bash
export HANDSFREE_AUTH_MODE=dev
```
- Accepts `X-User-Id` header for testing
- Falls back to a fixture user ID if no header is provided
- **Not for production use**

#### JWT Mode
```bash
export HANDSFREE_AUTH_MODE=jwt
export JWT_SECRET_KEY=your-secret-key
export JWT_ALGORITHM=HS256  # optional, defaults to HS256
```
- Requires valid JWT bearer tokens
- Extracts `user_id` from token claims (`user_id`, `sub`, or `uid`)
- Suitable for integration with existing auth systems

#### API Key Mode
```bash
export HANDSFREE_AUTH_MODE=api_key
```
- Requires API keys stored in DuckDB
- Keys are hashed with SHA256 (never stored in plaintext)
- Suitable for mobile clients and service-to-service auth

**Creating API Keys:**

Use the CLI tool to manage API keys:

```bash
# Create a new API key
python scripts/manage_api_keys.py create USER_ID --label "Mobile app"

# List API keys for a user
python scripts/manage_api_keys.py list USER_ID

# Revoke an API key
python scripts/manage_api_keys.py revoke USER_ID KEY_ID
```

Or use the API endpoints (requires authentication):

```bash
# Create a new API key
curl -X POST http://localhost:8080/v1/admin/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label": "Mobile app"}'

# List your API keys
curl http://localhost:8080/v1/admin/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN"

# Revoke an API key
curl -X DELETE http://localhost:8080/v1/admin/api-keys/KEY_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Using API Keys:**

Once created, use the API key as a bearer token:

```bash
curl http://localhost:8080/v1/command \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Production Considerations

- **Secrets**: Never bake secrets into the image. Use environment variables or secret management systems.
- **Database**: Mount a persistent volume for `/app/data` to preserve the DuckDB database.
- **Redis**: For production, use a managed Redis service or ensure Redis has persistent storage.
- **Auth**: Change `HANDSFREE_AUTH_MODE` to `jwt` or `api_key` for production deployments.
- **Metrics**: Enable metrics with `HANDSFREE_ENABLE_METRICS=true` for observability.

## Development Commands

| Command | Description |
|---------|-------------|
| `make deps` | Install Python development dependencies |
| `make fmt` | Auto-format code with Ruff |
| `make fmt-check` | Check code formatting (CI-equivalent) |
| `make lint` | Run Ruff linter |
| `make test` | Run pytest test suite |
| `make openapi-validate` | Validate OpenAPI specification |
| `make compose-up` | Start Redis container |
| `make compose-down` | Stop and remove containers |
| `make dev` | Start backend server (added in PR-002) |

## CI Checks

Pull requests automatically run:
- Format check (`make fmt-check`)
- Linting (`make lint`)
- Tests (`make test`)
- OpenAPI validation (`make openapi-validate`)

See `.github/workflows/ci.yml` for the full CI configuration.

## Project Structure

```
lift_coding/
├── .github/workflows/     # CI/CD workflows
├── implementation_plan/   # Design docs and PR specs
├── spec/                  # OpenAPI specification
├── src/handsfree/         # Main application code
├── tests/                 # Test suite with fixtures
│   └── fixtures/          # Canonical test fixtures
├── scripts/               # Utility scripts
├── tracking/              # PR tracking documents
└── Makefile               # Development commands
```

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and best practices
- [SECURITY.md](SECURITY.md) - Security policies and reporting
- [Agent Runner Setup](docs/agent-runner-setup.md) - Guide for setting up external agent runners
- `implementation_plan/` - Detailed design documents and PR specifications