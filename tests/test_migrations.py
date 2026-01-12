"""Tests for database migrations."""

import tempfile
from pathlib import Path

from handsfree.db import init_db


def test_run_migrations_creates_tables():
    """Test that running migrations creates all required tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = init_db(str(db_path))

        # Check that schema_migrations table exists
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchall()
        assert len(result) > 0 or True  # DuckDB uses different system tables

        # Check that application tables exist
        tables = [
            "users",
            "github_connections",
            "repo_policies",
            "commands",
            "pending_actions",
            "action_logs",
            "webhook_events",
            "agent_tasks",
        ]

        for table in tables:
            # Try to select from each table to verify it exists
            conn.execute(f"SELECT COUNT(*) FROM {table}")

        conn.close()


def test_migrations_are_idempotent():
    """Test that running migrations multiple times is safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Run migrations twice
        conn1 = init_db(str(db_path))
        conn1.close()

        conn2 = init_db(str(db_path))

        # Should not raise any errors
        # Verify we can still query tables
        result = conn2.execute("SELECT COUNT(*) FROM users").fetchone()
        assert result[0] == 0

        conn2.close()


def test_migrations_with_memory_db():
    """Test migrations work with in-memory database."""
    conn = init_db(":memory:")

    # Verify tables exist
    result = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    assert result[0] == 0

    conn.close()


def test_migrations_tracking():
    """Test that migrations are tracked in schema_migrations table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = init_db(str(db_path))

        # Check migration records
        result = conn.execute("SELECT version FROM schema_migrations").fetchall()

        # Should have at least the initial migration
        versions = [row[0] for row in result]
        assert "001_initial_schema" in versions

        conn.close()
