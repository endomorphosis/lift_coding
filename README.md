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