"""Database migrations module for HandsFree."""

from pathlib import Path

import duckdb


def run_migrations(conn: duckdb.DuckDBPyConnection | str) -> None:
    """Run all pending database migrations.

    Args:
        conn: DuckDB connection or database path string.
    """
    # If a string path is provided, open connection
    if isinstance(conn, str):
        conn = duckdb.connect(conn)

    # Get migrations directory path
    repo_root = Path(__file__).parent.parent.parent.parent
    migrations_dir = repo_root / "migrations"

    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    # Get all .sql migration files, sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        return  # No migrations to run

    # Create migrations tracking table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Get already applied migrations
    applied = set(
        row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    )

    # Apply pending migrations
    for migration_file in migration_files:
        version = migration_file.stem  # e.g., "001_initial_schema"

        if version in applied:
            continue

        # Read and execute migration
        sql = migration_file.read_text()
        conn.execute(sql)

        # Record migration as applied
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", [version])

        print(f"Applied migration: {version}")
