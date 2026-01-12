PR-004: Command system (intent parsing + profiles + confirmations)

This branch exists to host a draft PR for Copilot agents.

- Spec: implementation_plan/prs/PR-004-command-router-and-confirmations.md
- Tracking: tracking/PR-004-command-router-and-confirmations.md

## Agent checklist
- [x] Implement spec
- [x] Add fixtures + tests
- [x] Keep OpenAPI contract green

## Implementation Summary

### Completed (Commit ef7b153)

**Core Components:**
1. **IntentParser** (`src/handsfree/commands/intent_parser.py`)
   - Regex-based pattern matching for text transcripts
   - Supports 15+ intent types across 5 domains
   - Deterministic, fixture-validated parsing

2. **Profile System** (`src/handsfree/commands/profiles.py`)
   - workout/kitchen/commute/default profiles
   - Configurable verbosity (15-40 words)
   - Confirmation strictness control

3. **PendingActionManager** (`src/handsfree/commands/pending_actions.py`)
   - Secure token generation
   - Automatic expiry (60s default)
   - Confirm/cancel operations
   - In-memory storage (Redis-ready)

4. **CommandRouter** (`src/handsfree/commands/router.py`)
   - Profile-aware response composition
   - Automatic confirmation flow for side-effects
   - Session-based system.repeat
   - Integration stubs for PR-005/PR-007

**Testing:**
- 82 tests, 100% passing
- Clean/noisy/negative transcript fixtures
- Unit tests for all components
- Fixture-based integration tests

**CI Status:**
- ✅ make fmt-check
- ✅ make lint
- ✅ make test
- ✅ make openapi-validate

**Documentation:**
- README.md with usage examples
- Pattern addition guide
- Test organization guide

### How to Run Tests

```bash
# All tests
make test

# Specific test file
python3 -m pytest tests/test_intent_parser.py -v

# Fixture tests only
python3 -m pytest tests/test_fixtures.py -v
```

### Adding New Transcript Fixtures

1. Add examples to `tests/fixtures/transcripts/clean/<intent>.txt`
2. Add noisy variations to `tests/fixtures/transcripts/noisy/<intent>.txt`
3. Tests automatically pick up new fixtures

### Acceptance Criteria Status

✅ Given transcript fixtures, intent parser returns deterministic ParsedIntent
✅ Confirmation flow works end-to-end with token create/confirm/expire
✅ system.repeat replays last spoken response (or last command result) per user session

### Out of Scope (Future PRs)

- Real GitHub behavior and summaries (PR-005)
- Real side effects like requesting reviews (PR-007)
- Redis-backed persistence (can use PR-003 when available)

