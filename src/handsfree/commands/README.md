# Command System (PR-004)

This directory implements the command system for the hands-free dev companion, including intent parsing, profile-based response tuning, and confirmation flow for side-effect actions.

## Components

### Intent Parser (`intent_parser.py`)
Parses text transcripts into structured intents using regex pattern matching.

Supported intents:
- **System**: `system.repeat`, `system.confirm`, `system.cancel`, `system.set_profile`
- **Inbox**: `inbox.list`
- **PR**: `pr.summarize`, `pr.request_review`, `pr.merge`
- **Checks**: `checks.status`
- **Agent**: `agent.delegate`, `agent.progress`

### Profiles (`profiles.py`)
Context profiles that tune response verbosity and confirmation strictness:
- **workout**: Shortest responses (15 words), requires confirmation
- **kitchen**: Longer step-by-step (40 words), slower speech, requires confirmation
- **commute**: Medium verbosity (30 words), fewer interruptions
- **default**: Balanced (25 words), no forced confirmations

### Pending Actions (`pending_actions.py`)
Manages pending actions that require user confirmation before execution.

Features:
- Secure token generation
- Automatic expiry (default 60s)
- Confirm/cancel operations
- In-memory storage (can be swapped for Redis in production)

### Command Router (`router.py`)
Routes parsed intents to appropriate handlers and composes responses.

Features:
- Automatic confirmation flow for side-effect intents
- Profile-aware response formatting
- Session-based `system.repeat` functionality
- Integration with GitHub API for live execution when authenticated
- Agent orchestration for task delegation

## Usage

```python
from handsfree.commands import IntentParser, CommandRouter, PendingActionManager, Profile

# Initialize components
parser = IntentParser()
pending_mgr = PendingActionManager()
router = CommandRouter(pending_mgr)

# Parse and route a command
intent = parser.parse("summarize pr 412")
response = router.route(intent, Profile.WORKOUT, session_id="user123")

print(response["spoken_text"])
# Output: "PR 412: command system."
```

## Testing

Tests are organized into:

### Unit Tests
- `tests/test_intent_parser.py` - Intent parsing with various phrasings
- `tests/test_pending_actions.py` - Token lifecycle, expiry, confirm/cancel
- `tests/test_profiles.py` - Profile configuration
- `tests/test_router.py` - Response composition and routing

### Fixture Tests
- `tests/test_fixtures.py` - Tests using transcript fixtures
- `tests/fixtures/transcripts/clean/` - Clean transcript examples
- `tests/fixtures/transcripts/noisy/` - Noisy transcripts with filler words
- `tests/fixtures/transcripts/negative/` - Examples that should not match

Run tests:
```bash
make test
```

## Adding New Intents

To add a new intent:

1. Add regex pattern to `IntentParser.__init__()` in `intent_parser.py`
2. Add handler method to `CommandRouter` in `router.py`
3. Create clean and noisy transcript fixtures in `tests/fixtures/transcripts/`
4. Add unit tests in `tests/test_intent_parser.py`
5. Update this README

### Example Pattern

```python
(
    re.compile(r"\bmy\s+new\s+command\s+(\d+)\b", re.IGNORECASE),
    "domain.action",
    {"entity_name": lambda m: int(m.group(1))},
)
```

## CI Requirements

All code must pass:
- `make fmt-check` - Code formatting
- `make lint` - Linting checks
- `make test` - All tests
- `make openapi-validate` - API schema validation

## Future Work

- Enhanced machine learning-based intent classification (beyond regex)
- Multi-turn conversation support with context tracking
- Voice-specific error recovery and clarification flows
- Redis-backed pending action storage for production scalability
