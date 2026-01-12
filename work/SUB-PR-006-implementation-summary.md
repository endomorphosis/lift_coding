# SUB-PR-006: DB-backed webhook event store - Implementation Summary

## Overview
This PR implements persistent webhook event storage using DuckDB, replacing the in-memory implementation with a database-backed solution. This provides:
- Persistent replay protection across process restarts
- Event history/audit trail
- Simple dev mode (embedded DuckDB, no external services required)

## What Changed

### 1. Added DuckDB dependency
- Added `duckdb==1.1.3` to `requirements-dev.txt`

### 2. Created DB persistence layer
- **`src/handsfree/db/__init__.py`**: Database connection management
  - Configurable DB path via `HANDSFREE_DB_PATH` environment variable
  - Defaults to `~/.handsfree/handsfree.duckdb`
  - Auto-runs migrations on import for simple dev mode
  
- **`src/handsfree/db/migrations/001_webhook_events.sql`**: Initial migration
  - Creates `webhook_events` table with replay protection index
  - Unique index on `delivery_id` for efficient duplicate detection
  
- **`src/handsfree/db/webhook_events.py`**: DB-backed webhook store
  - `DBWebhookStore` class with same interface as in-memory store
  - `is_duplicate_delivery()`: DB-backed replay protection
  - `store_event()`: Persist webhook events
  - `get_event()`: Retrieve events by ID
  - `list_events()`: Query recent events

### 3. Updated webhook ingestion
- **`src/handsfree/api.py`**: Switched to DB-backed store
  - Changed from `get_webhook_store()` to `get_db_webhook_store()`
  - All webhook events now persist to DuckDB
  
### 4. Updated tests
- **`tests/test_webhooks.py`**: 
  - Updated fixture to clean DB before each test
  - Added 3 new DB-specific tests:
    - `test_db_store_persists_events`: Verify events are persisted
    - `test_db_replay_protection_across_sessions`: Verify replay protection survives restarts
    - `test_db_list_events`: Verify event queries work
  - All 15 tests pass

## Configuration

### Default (Dev Mode)
No configuration needed! Database auto-initializes at `~/.handsfree/handsfree.duckdb` on first use.

### Custom Database Path
Set environment variable:
```bash
export HANDSFREE_DB_PATH=/path/to/custom/handsfree.duckdb
```

### Testing
Tests automatically use a fresh database in the default location. Each test clears the webhook_events table via the `reset_webhook_store` fixture.

## Migration Instructions

### For Development
1. Install dependencies: `make deps`
2. Run tests: `make test`
3. Database is automatically created/migrated on first import

### For Production
1. Set `HANDSFREE_DB_PATH` to desired location
2. On first startup, migrations run automatically
3. For explicit migration control, import and call:
   ```python
   from handsfree.db import init_db
   init_db()
   ```

## Acceptance Criteria

✅ **Cherry-pick/rebase minimal DB webhook_events persistence code**
- Implemented fresh DB layer inspired by PR-003 plan
- Used DuckDB as specified in implementation plan

✅ **Replace in-memory webhook store with DB-backed store**
- `api.py` now uses `DBWebhookStore`
- Events persist with all required fields: `delivery_id`, `event_type`, `payload`, `signature_ok`

✅ **Implement replay protection via DB**
- Unique index on `delivery_id` ensures no duplicates
- `is_duplicate_delivery()` checks DB instead of in-memory set
- Protection survives process restarts

✅ **Keep existing tests passing**
- All 11 original tests pass with DB backend
- Tests use DB cleanup fixture

✅ **Add DB-backed tests**
- 3 new tests verify DB persistence and replay protection

✅ **Keep dev mode simple**
- No external DB service required
- Embedded DuckDB auto-initializes
- Default path in home directory

✅ **Keep CI green**
- All tests pass (15/15)
- `make fmt-check` ✓
- `make lint` ✓
- `make test` ✓
- `make openapi-validate` ✓

## Architecture Notes

### Why not keep in-memory store?
The in-memory store loses replay protection on restart, which could allow duplicate webhook processing. DB-backed storage provides:
- Durable replay protection
- Event audit trail
- Foundation for future inbox/notification features

### Why DuckDB?
- Embedded (no separate process/service)
- SQL-based (familiar, powerful queries)
- Fast for analytical workloads
- Matches implementation plan (docs/04-backend.md)

### Performance Considerations
- Unique index on `delivery_id` makes duplicate checks O(log n)
- DuckDB is optimized for OLAP, suitable for event storage
- For high-throughput scenarios, consider Redis for hot duplicate detection (future work)

## Future Work (Out of Scope)
- Full inbox state projection from normalized events
- Mobile notifications
- Redis integration for hot replay detection cache
- Event retention policies
- Event replay/reprocessing tools
