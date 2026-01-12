# PR-003 Implementation: Database Migrations & Persistence Primitives

## Overview
This PR implements DuckDB-based persistence layer with migrations framework for the HandsFree dev companion.

## What Was Implemented

### 1. Migrations Framework
- **Location**: `migrations/` directory
- **Initial migration**: `001_initial_schema.sql` - Complete database schema
- **Migration runner**: `scripts/migrate.py` - Applies pending migrations
- **Tracking**: Uses `schema_migrations` table to track applied migrations

### 2. Database Connection Module
- **Location**: `src/handsfree/db/connection.py`
- **Features**:
  - Environment-based configuration (`DUCKDB_PATH`)
  - Support for in-memory databases (`:memory:`)
  - Automatic directory creation for file-based databases

### 3. Persistence APIs

#### Pending Actions (`src/handsfree/db/pending_actions.py`)
- Create pending actions with auto-generated secure tokens
- Token-based retrieval with automatic expiry checking
- Delete actions after confirmation/cancellation
- Cleanup expired actions

#### Action Logs (`src/handsfree/db/action_logs.py`)
- Write audit logs for side-effect actions
- Idempotency key support to prevent duplicates
- Query logs by user, action type, etc.
- Pagination support

#### Webhook Events (`src/handsfree/db/webhook_events.py`)
- Store incoming webhook events
- Track signature validation status
- Query by source, event type, signature validity
- Full payload storage for replay/debugging

#### Commands (`src/handsfree/db/commands.py`)
- Store command history with parsed intents
- **Privacy feature**: Optional transcript storage (disabled by default)
- Track intent confidence and extracted entities
- Query by user, profile, status

## Usage Examples

### Running Migrations
```bash
# Using default database path (data/handsfree.db)
python scripts/migrate.py

# Using custom database path
python scripts/migrate.py --db-path /path/to/database.db

# Set via environment variable
export DUCKDB_PATH=/path/to/database.db
python scripts/migrate.py
```

### Using Persistence APIs
```python
from handsfree.db import init_db
from handsfree.db.pending_actions import create_pending_action, get_pending_action
from handsfree.db.action_logs import write_action_log
from handsfree.db.webhook_events import store_webhook_event
from handsfree.db.commands import store_command

# Initialize database (runs migrations)
conn = init_db()

# Create a pending action
action = create_pending_action(
    conn,
    user_id="user-uuid",
    summary="Merge PR #123",
    action_type="merge_pr",
    action_payload={"repo": "owner/repo", "pr_number": 123},
    expires_in_seconds=3600,
)
print(f"Action token: {action.token}")

# Write an action log
log = write_action_log(
    conn,
    user_id="user-uuid",
    action_type="merge_pr",
    ok=True,
    target="owner/repo#123",
    idempotency_key="unique-key-123",
)

# Store a webhook event
event = store_webhook_event(
    conn,
    source="github",
    signature_ok=True,
    event_type="push",
    payload={"ref": "refs/heads/main"},
)

# Store a command (privacy: transcript not stored by default)
command = store_command(
    conn,
    user_id="user-uuid",
    input_type="text",
    status="ok",
    transcript="merge the PR",  # Won't be stored
    intent_name="merge_pr",
    store_transcript=False,  # Explicit privacy control
)

conn.close()
```

## Testing
All persistence modules have comprehensive test coverage:
- `tests/test_migrations.py` - Migration framework tests
- `tests/test_pending_actions.py` - Pending actions API tests
- `tests/test_action_logs.py` - Action logs API tests
- `tests/test_webhook_events.py` - Webhook events API tests
- `tests/test_commands.py` - Commands API tests

Run tests:
```bash
make test
```

## CI Validation
All CI checks pass:
```bash
make fmt-check  # Code formatting
make lint       # Linting
make test       # Tests
make openapi-validate  # OpenAPI spec validation
```

## Key Design Decisions

1. **Simple SQL Migrations**: No heavyweight migration framework - just numbered SQL files applied in order
2. **Privacy by Default**: Command transcripts not stored unless explicitly enabled
3. **Idempotency Support**: Action logs can use idempotency keys to prevent duplicates
4. **JSON Storage**: DuckDB's JSON support used for flexible payload storage
5. **In-Memory Testing**: All tests use `:memory:` databases for speed
6. **No HTTP Integration**: Not wired into API routes to avoid conflicts with PR-002

## Dependencies Added
- `duckdb==1.1.3` - Embedded database
- `redis==5.2.1` - For future session/dedupe support

## File Structure
```
migrations/
  001_initial_schema.sql    # Initial database schema
  README.md                 # Migration documentation

scripts/
  migrate.py               # Migration runner script

src/handsfree/db/
  __init__.py              # Package exports
  connection.py            # Database connection management
  migrations.py            # Migration framework
  pending_actions.py       # Pending actions persistence
  action_logs.py           # Action logs persistence
  webhook_events.py        # Webhook events persistence
  commands.py              # Commands persistence

tests/
  conftest.py              # Test configuration
  test_migrations.py       # Migration tests
  test_pending_actions.py  # Pending actions tests
  test_action_logs.py      # Action logs tests
  test_webhook_events.py   # Webhook events tests
  test_commands.py         # Commands tests
```
