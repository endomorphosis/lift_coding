# Database Migrations

This directory contains SQL migration files for the DuckDB schema.

## Migration Files

Migration files are numbered sequentially and applied in order:
- `001_initial_schema.sql` - Initial database schema

## Running Migrations

Use the migration script to apply all pending migrations:

```bash
python scripts/migrate.py
```

Or use it programmatically:

```python
from handsfree.db.migrations import run_migrations

run_migrations(db_path="path/to/database.db")
```

## Adding New Migrations

1. Create a new file with the next sequential number: `00X_description.sql`
2. Write idempotent SQL statements (use `IF NOT EXISTS` where appropriate)
3. Test the migration on a copy of the production schema
4. Add migration to version control
