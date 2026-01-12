"""Database connection and configuration for DuckDB."""

import logging
import os
import pathlib
from contextlib import contextmanager

import duckdb

logger = logging.getLogger(__name__)

# Default DB path for development
DEFAULT_DB_PATH = pathlib.Path.home() / ".handsfree" / "handsfree.duckdb"


def get_db_path() -> pathlib.Path:
    """Get the DuckDB database file path from environment or use default."""
    db_path_str = os.environ.get("HANDSFREE_DB_PATH")
    if db_path_str:
        return pathlib.Path(db_path_str)
    return DEFAULT_DB_PATH


def ensure_db_dir() -> None:
    """Ensure the database directory exists."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Get a DuckDB connection context manager.

    Yields:
        duckdb.DuckDBPyConnection: Database connection
    """
    ensure_db_dir()
    db_path = get_db_path()
    conn = duckdb.connect(str(db_path))
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database with the schema.

    Runs all migrations in order.
    """
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    with get_connection() as conn:
        for migration_file in migration_files:
            logger.info("Running migration: %s", migration_file.name)
            sql = migration_file.read_text(encoding="utf-8")
            conn.execute(sql)

        logger.info("Database initialized successfully")


# Initialize the database when the module is imported
# This is safe for embedded DuckDB and makes dev mode simple
try:
    init_db()
except Exception as e:
    logger.warning(
        "Failed to initialize database at %s: %s. "
        "Database operations may fail. Check that the directory exists and is writable.",
        get_db_path(),
        e,
    )
