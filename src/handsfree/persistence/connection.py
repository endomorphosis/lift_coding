"""Database connection configuration."""

import os

import duckdb


def get_db_path() -> str:
    """Get the database file path from environment or use default."""
    return os.environ.get("DB_PATH", "data/handsfree.duckdb")


def get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Get a DuckDB connection.

    Args:
        db_path: Optional path to database file. If None, uses DB_PATH env var or default.
                 Use ":memory:" for in-memory database (useful for tests).

    Returns:
        DuckDB connection object.
    """
    if db_path is None:
        db_path = get_db_path()

    # Ensure data directory exists for file-based databases
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    return duckdb.connect(db_path)
