# Persistent Database Configuration

## Overview

The HandsFree backend now uses a **persistent file-backed DuckDB database** by default, ensuring data survives server restarts. Tests remain fast and isolated by using in-memory databases.

## Configuration

### Default Behavior (Production/Development)

By default, the server stores data in:
```
data/handsfree.db
```

This can be customized via the `DUCKDB_PATH` environment variable:

```bash
export DUCKDB_PATH=/path/to/your/database.db
python -m handsfree.server
```

### Test Behavior

Tests automatically use an in-memory database (`:memory:`) for:
- Fast execution
- Complete isolation between tests
- No cleanup required

This is configured in `tests/conftest.py` by setting:
```python
os.environ["DUCKDB_PATH"] = ":memory:"
```

## Implementation Details

### Key Changes

1. **`src/handsfree/api.py`**: 
   - Changed `get_db()` to call `init_db()` without arguments
   - Now uses `get_db_path()` from `connection.py` which reads `DUCKDB_PATH` env var

2. **`tests/conftest.py`**:
   - Sets `DUCKDB_PATH=:memory:` for all tests
   - Ensures test isolation and performance

### Database Path Resolution

The database path is resolved in this order:

1. `DUCKDB_PATH` environment variable (if set)
2. Default: `data/handsfree.db`

The `data/` directory is already in `.gitignore` to prevent committing database files.

## Usage Examples

### Start Server with Default Database
```bash
python -m handsfree.server
# Data stored in: data/handsfree.db
```

### Start Server with Custom Database
```bash
export DUCKDB_PATH=/var/lib/handsfree/prod.db
python -m handsfree.server
```

### Run Tests (Automatic Memory DB)
```bash
make test
# Tests use :memory: automatically
```

## Migration Behavior

Migrations run automatically on startup via `init_db()`, regardless of whether using file-based or in-memory databases. This ensures schema consistency across all environments.

## Benefits

✅ **Data Persistence**: Server data survives restarts  
✅ **Fast Tests**: In-memory databases for test speed  
✅ **Test Isolation**: Each test gets a fresh database  
✅ **Flexible Configuration**: Easy to customize via environment variable  
✅ **Backward Compatible**: Existing tests work without modification
