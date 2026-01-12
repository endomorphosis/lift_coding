#!/usr/bin/env python3
"""
Simple migration runner for DuckDB.

Applies SQL migrations from the migrations/ directory in order.
Tracks applied migrations in a migrations_history table.
"""

import argparse
import os
import sys
from pathlib import Path

import duckdb


def get_db_path() -> str:
    """Get the database file path from environment or use default."""
    return os.environ.get("DB_PATH", "data/handsfree.duckdb")


def ensure_migrations_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create migrations_history table if it doesn't exist."""
    conn.execute("CREATE SEQUENCE IF NOT EXISTS migrations_history_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations_history (
            id INTEGER PRIMARY KEY DEFAULT nextval('migrations_history_seq'),
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def get_applied_migrations(conn: duckdb.DuckDBPyConnection) -> set[str]:
    """Return set of migration names that have been applied."""
    result = conn.execute("SELECT migration_name FROM migrations_history").fetchall()
    return {row[0] for row in result}


def get_pending_migrations(migrations_dir: Path, applied: set[str]) -> list[Path]:
    """Return list of pending migration files in sorted order."""
    all_migrations = sorted(migrations_dir.glob("*.sql"))
    pending = [m for m in all_migrations if m.name not in applied]
    return pending


def apply_migration(conn: duckdb.DuckDBPyConnection, migration_file: Path) -> None:
    """Apply a single migration file."""
    print(f"Applying migration: {migration_file.name}")
    sql_content = migration_file.read_text()

    # Execute the migration SQL
    conn.execute(sql_content)

    # Record in migrations_history
    conn.execute(
        "INSERT INTO migrations_history (migration_name) VALUES (?)",
        [migration_file.name],
    )

    print(f"✓ Applied migration: {migration_file.name}")


def main() -> int:
    """Run migrations."""
    parser = argparse.ArgumentParser(description="Run DuckDB migrations")
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path(__file__).parent.parent / "migrations",
        help="Path to migrations directory",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to DuckDB database file (overrides DB_PATH env var)",
    )
    args = parser.parse_args()

    # Determine database path
    db_path = args.db_path or get_db_path()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    print(f"Database: {db_path}")
    print(f"Migrations directory: {args.migrations_dir}")

    if not args.migrations_dir.exists():
        print(f"Error: Migrations directory not found: {args.migrations_dir}")
        return 1

    # Connect to database
    conn = duckdb.connect(db_path)

    try:
        # Ensure migrations tracking table exists
        ensure_migrations_table(conn)

        # Get applied and pending migrations
        applied = get_applied_migrations(conn)
        pending = get_pending_migrations(args.migrations_dir, applied)

        if not pending:
            print("No pending migrations.")
            return 0

        print(f"Found {len(pending)} pending migration(s):")
        for migration in pending:
            print(f"  - {migration.name}")

        # Apply each pending migration
        for migration in pending:
            apply_migration(conn, migration)

        conn.commit()
        print(f"\n✓ Successfully applied {len(pending)} migration(s).")
        return 0

    except Exception as e:
        print(f"\n✗ Error applying migrations: {e}", file=sys.stderr)
        conn.rollback()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
