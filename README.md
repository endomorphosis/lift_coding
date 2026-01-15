# Handsfree Dev Companion

A proof-of-concept AI companion for GitHub that helps manage pull requests, issues, and code reviews using fixture-based development and safe policy-driven automation.

## Stack

- **DuckDB** (embedded) for persistence
- **Redis** for caching and job queues
- **Python 3.11+** with FastAPI (backend server added in PR-002)

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
- `implementation_plan/` - Detailed design documents and PR specifications