# HandsFree Dev Companion

A hands-free assistant that lets you stay productive while your hands are occupied (lifting, cooking, walking, commuting). It connects wearable inputs (voice + optional camera) to developer workflows (PRs, issues, CI, agent tasks) and returns short, safe, spoken feedback.

## Features

- **PR inbox + spoken summaries**: Stay updated on pull requests without touching your keyboard
- **CI / check status and alerts**: Monitor build status and get notified of failures
- **Safe actions**: Comment, request review, rerun checks, merge-under-policy with confirmation gates
- **Agent delegation**: Delegate tasks to coding agents (Copilot or custom agents) with progress updates
- **Context profiles**: Different modes for Workout, Kitchen, Walk, Commute

## Tech Stack

- **Database**: DuckDB (embedded) for local storage
- **Cache**: Redis for session management and real-time data
- **API**: OpenAPI-first design (see `spec/openapi.yaml`)
- **Backend**: Python with FastAPI (implemented in PR-002+)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Make

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/endomorphosis/lift_coding.git
   cd lift_coding
   ```

2. **Install dependencies**
   ```bash
   make deps
   ```

3. **Start infrastructure services**
   ```bash
   make compose-up
   ```
   
   This starts Redis in Docker. DuckDB runs embedded and requires no separate service.

4. **Run the development server** (available in PR-002+)
   ```bash
   make dev
   ```

5. **Stop infrastructure services**
   ```bash
   make compose-down
   ```

### Development Commands

- `make fmt` - Format code with Ruff
- `make fmt-check` - Check code formatting without modifying files
- `make lint` - Run linting checks
- `make test` - Run test suite
- `make openapi-validate` - Validate OpenAPI specification
- `make compose-up` - Start Docker Compose services (Redis)
- `make compose-down` - Stop Docker Compose services

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/test_example.py
```

## Project Structure

```
.
├── spec/                    # OpenAPI specification
├── src/                     # Source code
├── tests/                   # Test suite
│   └── fixtures/           # Test fixtures (transcripts, webhooks, API samples)
├── implementation_plan/     # Design docs and PR specifications
├── scripts/                # Development and utility scripts
├── docker-compose.yml      # Docker services configuration
└── Makefile               # Development commands
```

## Documentation

- [Implementation Plan Overview](implementation_plan/docs/00-overview.md)
- [Security & Privacy Guidelines](SECURITY.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Development Loop](implementation_plan/docs/11-devloop-vscode.md)

For detailed design documentation, see the `implementation_plan/docs/` directory.

## Security

This project handles sensitive data including GitHub tokens and repository access. See [SECURITY.md](SECURITY.md) for:
- Redaction policies for logs and summaries
- Secret handling guidelines
- Threat model and security controls

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up your development environment
- Running tests and validation
- Submitting pull requests
- Code style and conventions

## License

See [LICENSE](LICENSE) for details.
