# Contributing to HandsFree Dev Companion

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Make
- Git

### Getting Started

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/lift_coding.git
   cd lift_coding
   ```

2. **Install development dependencies**
   ```bash
   make deps
   ```

3. **Start infrastructure services**
   ```bash
   make compose-up
   ```
   This starts Redis. DuckDB is embedded and requires no separate service.

4. **Run tests to verify setup**
   ```bash
   make test
   ```

## Development Workflow

### Before Making Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make sure all tests pass:
   ```bash
   make fmt-check lint test openapi-validate
   ```

### Making Changes

1. **Write tests first** (when applicable)
   - Add fixtures to `tests/fixtures/` for reproducible scenarios
   - Use transcript fixtures for intent parsing tests
   - Use webhook fixtures for GitHub integration tests

2. **Make your changes**
   - Follow existing code style and conventions
   - Keep changes focused and minimal
   - Update documentation if needed

3. **Validate your changes**
   ```bash
   make fmt          # Format code
   make lint         # Run linter
   make test         # Run tests
   make openapi-validate  # Validate OpenAPI spec if changed
   ```

### Code Style

- **Formatting**: We use Ruff for code formatting
  - Run `make fmt` to auto-format
  - Run `make fmt-check` to check without modifying

- **Linting**: We use Ruff for linting
  - Run `make lint` to check for issues
  - Fix all linting errors before submitting

- **Type Hints**: Use Python type hints where practical

### Testing

- Place test files in `tests/` directory
- Use fixtures from `tests/fixtures/` for deterministic tests
- Test transcript parsing with `tests/fixtures/transcripts/*.txt`
- Test GitHub integration with `tests/fixtures/github/*.json`
- Run tests with `make test` or `python3 -m pytest`

### Commit Guidelines

- Write clear, concise commit messages
- Use present tense ("Add feature" not "Added feature")
- Reference issue numbers when applicable
- Keep commits focused on a single change

Example:
```
Add webhook signature verification

- Implement HMAC-SHA256 verification for GitHub webhooks
- Add tests for valid and invalid signatures
- Update security docs with verification details

Fixes #123
```

### Submitting a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request**
   - Provide a clear description of changes
   - Reference related issues
   - Include testing details
   - Ensure CI passes

3. **Address review feedback**
   - Respond to comments
   - Make requested changes
   - Push updates to the same branch

## Project Structure

```
.
├── spec/                    # OpenAPI specification
│   └── openapi.yaml        # API contract (source of truth)
├── src/                     # Source code (backend implemented in PR-002+)
├── tests/                   # Test suite
│   └── fixtures/           # Test fixtures
│       ├── transcripts/    # Voice input examples
│       ├── github/         # Webhook and API response samples
│       └── api/            # Expected API responses
├── implementation_plan/     # Design documents
│   ├── docs/               # Architecture and design specs
│   └── prs/                # PR-specific implementation plans
├── scripts/                # Development utilities
├── docker-compose.yml      # Infrastructure services (Redis)
└── Makefile               # Development commands
```

## Development Best Practices

### Security

- **Never commit secrets**: See [SECURITY.md](SECURITY.md) for guidelines
- **Redact sensitive data**: Ensure logs don't contain tokens or private data
- **Validate input**: Sanitize user input and webhook payloads
- **Follow least privilege**: Request minimal GitHub permissions needed

### Fixtures and Replay

- Use fixtures to make tests deterministic
- Add new fixtures for new integration scenarios
- Test with webhook replay instead of live debugging
- Keep fixtures minimal but representative

### Documentation

- Update documentation when changing behavior
- Add inline comments for complex logic
- Keep README and SECURITY.md in sync with changes
- Document new environment variables in README

## Questions?

- Check existing [issues](https://github.com/endomorphosis/lift_coding/issues)
- Review [implementation plan docs](implementation_plan/docs/)
- Open a new issue for questions or bugs
- Join discussions in pull requests

## Code of Conduct

- Be respectful and constructive
- Focus on the issue, not the person
- Help create a welcoming environment for all contributors

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).
