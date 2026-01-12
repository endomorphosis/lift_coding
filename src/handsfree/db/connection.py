"""Database connection and configuration for HandsFree.

This module provides DuckDB connection management and basic configuration.
"""

import os
from pathlib import Path

import duckdb


def get_db_path() -> str:
    """Get the database file path from environment or default."""
    return os.getenv("DUCKDB_PATH", "data/handsfree.db")


def get_connection(
    db_path: str | None = None, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection.

    Args:
        db_path: Path to the database file. If None, uses get_db_path().
                If ":memory:", uses in-memory database.
        read_only: Whether to open in read-only mode.

    Returns:
        DuckDB connection object.
    """
    if db_path is None:
        db_path = get_db_path()

    # Ensure parent directory exists for file-based databases
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return duckdb.connect(db_path, read_only=read_only)


def init_db(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """Initialize database connection and run migrations.

    Args:
        db_path: Path to the database file. If None, uses get_db_path().

    Returns:
        DuckDB connection object.
    """
    conn = get_connection(db_path=db_path)

    # Import here to avoid circular dependency
    from handsfree.db.migrations import run_migrations

    run_migrations(conn)
    return conn
