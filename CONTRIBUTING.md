# Contributing to Handsfree Dev Companion

Thank you for your interest in contributing! This guide covers the development workflow and best practices for this project.

## Development Philosophy

This project follows a **fixtures-first** approach:

- Write fixtures (example inputs/outputs) before implementing features
- Keep fixtures in `tests/fixtures/` for reproducibility
- Use fixtures for both testing and development iteration
- Replay recorded GitHub webhooks and API responses for local dev

## Getting Started

1. **Fork and clone** the repository
2. **Install dependencies**: `make deps`
3. **Start services**: `make compose-up` (Redis)
4. **Run tests**: `make test`

## Running CI Checks Locally

Before pushing your changes, run the same checks that CI will run:

```bash
# 1. Format check
make fmt-check

# 2. Lint
make lint

# 3. Tests
make test

# 4. OpenAPI validation
make openapi-validate
```

Or auto-fix formatting issues:
```bash
make fmt
```

All checks must pass before a PR can be merged.

## Development Workflow

### 1. Create a Branch

Use descriptive branch names:
```bash
git checkout -b feature/your-feature-name
git checkout -b fix/issue-description
```

### 2. Write Tests First (Fixtures-First)

- Add or update fixtures in `tests/fixtures/`
- Write tests that use those fixtures
- Run tests to verify they fail: `make test`

### 3. Implement Changes

- Make minimal changes to satisfy the tests
- Follow existing code style (enforced by Ruff)
- Keep commits focused and atomic

### 4. Validate Locally

Run all CI checks:
```bash
make fmt-check lint test openapi-validate
```

### 5. Push and Create PR

```bash
git push origin your-branch-name
```

Then open a pull request on GitHub.

## Code Style

- **Python**: Follow Ruff formatting and linting rules (configured in `pyproject.toml`)
- **Line length**: 100 characters
- **Target**: Python 3.11+

The formatter and linter will catch most style issues automatically.

## Testing Guidelines

### Test Organization

- Unit tests: Test individual functions/classes
- Integration tests: Test component interactions
- Use fixtures from `tests/fixtures/` for realistic scenarios

### Fixtures-First Development

1. **Capture real data**: Record GitHub webhooks, API responses, or create representative examples
2. **Store as fixtures**: Save in `tests/fixtures/` with descriptive names
3. **Use in tests**: Load fixtures and verify behavior
4. **Iterate**: Replay fixtures during development for fast feedback

Example fixture structure:
```
tests/fixtures/
├── github_webhooks/
│   ├── issue_opened.json
│   └── pr_review_requested.json
├── github_api/
│   ├── issue_123.json
│   └── pr_456.json
└── transcripts/
    └── example_conversation.json
```

## Pull Request Guidelines

- **Title**: Clear and concise description of changes
- **Description**: Explain what, why, and how
- **Link issues**: Use "Fixes #123" or "Closes #456"
- **Keep scope small**: Focus on one feature or fix per PR
- **Request review**: Tag appropriate reviewers

## OpenAPI Changes

If you modify the API:

1. Update `spec/openapi.yaml`
2. Validate: `make openapi-validate`
3. Ensure backward compatibility or document breaking changes

## Questions?

- Check `implementation_plan/` for design documents
- Open a discussion issue for clarification
- Review existing PRs for examples

Thank you for contributing! 🚀
