# Contributing to HandsFree Dev Companion

Thank you for your interest in contributing! This guide covers the development workflow and best practices for this project.

## 📚 Quick Links

- **[Getting Started](GETTING_STARTED.md)** - Setup guide for new contributors
- **[Architecture](ARCHITECTURE.md)** - System design and components
- **[Configuration](CONFIGURATION.md)** - Environment setup
- **Backend Development** - See below
- **Mobile Development** - See [mobile/README.md](mobile/README.md)

---

## Development Philosophy

This project follows a **fixtures-first** approach:

- Write fixtures (example inputs/outputs) before implementing features
- Keep fixtures in `tests/fixtures/` for reproducibility
- Use fixtures for both testing and development iteration
- Replay recorded GitHub webhooks and API responses for local dev

## Getting Started

### For Backend Development

1. **Fork and clone** the repository
2. **Install dependencies**: `make deps`
3. **Start services**: `make compose-up` (Redis)
4. **Run tests**: `make test`

See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup.

### For Mobile Development

1. **Setup backend** (see above)
2. **Navigate to mobile**: `cd mobile`
3. **Install dependencies**: `npm ci`
4. **Run on simulator**: `npm run ios` or `npm run android`

See [mobile/README.md](mobile/README.md) for detailed mobile development guide.

---

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
git checkout -b mobile/feature-name  # for mobile-specific features
```

### 2. Write Tests First (Fixtures-First)

**Backend**:
- Add or update fixtures in `tests/fixtures/`
- Write tests that use those fixtures
- Run tests to verify they fail: `make test`

**Mobile**:
- Add unit tests for components: `mobile/src/__tests__/`
- Test API client methods
- Verify on simulator before testing on device

### 3. Implement Changes

- Make minimal changes to satisfy the tests
- Follow existing code style (enforced by Ruff for Python)
- Keep commits focused and atomic
- Write clear commit messages

**Backend Style**:
- Python 3.11+ features
- Type hints where appropriate
- Docstrings for public APIs
- Follow PEP 8 (enforced by Ruff)

**Mobile Style**:
- React hooks for state management
- Functional components (not class components)
- PropTypes or TypeScript for type checking
- Consistent naming conventions

### 4. Validate Locally

**Backend**:
```bash
make fmt-check  # Check formatting
make lint       # Run linter
make test       # Run tests
make openapi-validate  # Validate API spec
```

**Mobile**:
```bash
cd mobile
npm run lint    # Run ESLint (if configured)
npm test        # Run tests (if configured)
# Test on simulator/device
```

### 5. Push and Create PR

```bash
git push origin your-branch-name
```

Then open a pull request on GitHub.

---

## Code Style

### Python (Backend)

- **Formatter**: Ruff (configured in `pyproject.toml`)
- **Linter**: Ruff
- **Line length**: 100 characters
- **Target**: Python 3.11+
- **Type hints**: Encouraged for public APIs
- **Docstrings**: Google style for public functions

**Auto-format**:
```bash
make fmt
```

The formatter and linter will catch most style issues automatically.

### JavaScript/React Native (Mobile)

- **Style**: Airbnb React/JavaScript style guide
- **Components**: Functional components with hooks
- **State**: React hooks (`useState`, `useEffect`)
- **Naming**:
  - Components: PascalCase (e.g., `CommandScreen.js`)
  - Functions: camelCase (e.g., `sendCommand`)
  - Constants: UPPER_SNAKE_CASE (e.g., `BASE_URL`)

**Linting** (if configured):
```bash
cd mobile
npm run lint
```

---

## Testing Guidelines

### Backend Testing

#### Test Organization

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions
- **Use fixtures** from `tests/fixtures/` for realistic scenarios

#### Fixtures-First Development

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

#### Running Tests

```bash
# All tests
make test

# Specific test file
pytest tests/test_command_processor.py

# With coverage
pytest --cov=handsfree tests/

# Verbose output
pytest -v tests/
```

### Mobile Testing

#### Manual Testing Checklist

Before submitting PR, test:

- [ ] **Status screen** - Backend connectivity
- [ ] **Command screen** - Text and voice commands
- [ ] **TTS playback** - Audio plays correctly
- [ ] **Settings** - Configuration persists
- [ ] **Bluetooth** - Works with glasses (if applicable)
- [ ] **Different devices** - iOS Simulator, Android Emulator, physical devices

#### Automated Testing (Future)

```bash
cd mobile
npm test
```

#### Testing on Physical Devices

**iOS**:
```bash
cd mobile
npx expo run:ios --device
```

**Android**:
```bash
cd mobile
npx expo run:android --device
```

---

## Pull Request Guidelines

- **Title**: Clear and concise description of changes
- **Description**: Explain what, why, and how
  - What problem does this solve?
  - What approach did you take?
  - Any breaking changes?
  - Testing performed?
- **Link issues**: Use "Fixes #123" or "Closes #456"
- **Keep scope small**: Focus on one feature or fix per PR
- **Request review**: Tag appropriate reviewers
- **Update documentation**: If you change APIs or add features
- **Add tests**: All new code should have tests

### PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
- [ ] Tested locally
- [ ] Added/updated tests
- [ ] Tested on iOS/Android (if mobile changes)

## Related Issues
Fixes #123

## Screenshots
(If UI changes)
```

---

## Mobile-Specific Guidelines

### Native Module Development

When working on native iOS/Android modules (Bluetooth integration):

1. **Test on physical device** - Simulators don't support Bluetooth
2. **iOS changes**:
   - Update Swift code in `mobile/modules/expo-glasses-audio/ios/`
   - Run `pod install` after changes
   - Test on iPhone with glasses connected
3. **Android changes**:
   - Update Kotlin code in `mobile/modules/expo-glasses-audio/android/`
   - Test on Android device with Bluetooth headset

### Audio Testing

For changes affecting audio (recording, playback, routing):

1. Test with phone mic/speaker
2. Test with Bluetooth headset
3. Test with Meta AI Glasses
4. Verify audio routes correctly
5. Check for echo or feedback issues

### Push Notifications

For notification-related changes:

1. Test on physical device (push doesn't work in simulator)
2. Verify foreground behavior
3. Verify background behavior
4. Test notification permissions flow
5. Check auto-speaking feature (if enabled)

---

## API Changes

If you modify the API:

1. Update `spec/openapi.yaml`
2. Validate: `make openapi-validate`
3. Ensure backward compatibility or document breaking changes
4. Update mobile app if endpoints change
5. Update API documentation

---

## Documentation

When adding features or changing behavior:

1. **Update relevant docs**:
   - [GETTING_STARTED.md](GETTING_STARTED.md) - If setup changes
   - [ARCHITECTURE.md](ARCHITECTURE.md) - If architecture changes
   - [CONFIGURATION.md](CONFIGURATION.md) - If config changes
   - [mobile/README.md](mobile/README.md) - If mobile features change

2. **Add inline documentation**:
   - Docstrings for Python functions
   - JSDoc comments for JavaScript functions
   - README updates for new directories

3. **Update examples**:
   - Code examples should be tested
   - Configuration examples should be valid

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped in:
  - `pyproject.toml` (backend)
  - `mobile/package.json` (mobile)
  - `mobile/app.json` (mobile)
- [ ] Tag created: `git tag v1.0.0`
- [ ] Release notes written

---

## Getting Help

### Documentation

- **[Getting Started](GETTING_STARTED.md)** - Setup guide
- **[Architecture](ARCHITECTURE.md)** - System design
- **[Mobile README](mobile/README.md)** - Mobile development
- **implementation_plan/** - Design documents

### Community

- **GitHub Issues** - Ask questions, report bugs
- **Discussions** - General questions and ideas
- **PR Comments** - Code-specific discussions

---

## Code of Conduct

### Our Standards

- **Be respectful** - Treat everyone with respect
- **Be collaborative** - Work together constructively
- **Be patient** - Remember everyone is learning
- **Be constructive** - Provide helpful feedback

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Publishing others' private information

### Reporting

Report violations to the project maintainers via GitHub Issues or email.

---

Thank you for contributing! 🚀
