"""Tests for database migrations."""

from pathlib import Path

from scripts.migrate import (
    apply_migration,
    ensure_migrations_table,
    get_applied_migrations,
    get_pending_migrations,
)
from src.handsfree.persistence import get_connection


def test_ensure_migrations_table():
    """Test that migrations_history table is created."""
    conn = get_connection(":memory:")
    ensure_migrations_table(conn)

    # Check table exists by trying to query it
    result = conn.execute("SELECT COUNT(*) FROM migrations_history").fetchone()
    assert result is not None


def test_get_applied_migrations():
    """Test retrieving applied migrations."""
    conn = get_connection(":memory:")
    ensure_migrations_table(conn)

    # Initially empty
    applied = get_applied_migrations(conn)
    assert applied == set()

    # Add a migration
    conn.execute(
        "INSERT INTO migrations_history (migration_name) VALUES (?)",
        ["001_test.sql"],
    )

    applied = get_applied_migrations(conn)
    assert applied == {"001_test.sql"}


def test_get_pending_migrations(tmp_path):
    """Test getting pending migrations."""
    # Create some migration files
    (tmp_path / "001_first.sql").write_text("SELECT 1;")
    (tmp_path / "002_second.sql").write_text("SELECT 2;")
    (tmp_path / "003_third.sql").write_text("SELECT 3;")

    # Test with no applied migrations
    pending = get_pending_migrations(tmp_path, set())
    assert len(pending) == 3
    assert pending[0].name == "001_first.sql"
    assert pending[1].name == "002_second.sql"
    assert pending[2].name == "003_third.sql"

    # Test with some applied
    pending = get_pending_migrations(tmp_path, {"001_first.sql", "002_second.sql"})
    assert len(pending) == 1
    assert pending[0].name == "003_third.sql"


def test_apply_migration(tmp_path):
    """Test applying a migration."""
    conn = get_connection(":memory:")
    ensure_migrations_table(conn)

    # Create a simple migration
    migration_file = tmp_path / "001_create_test.sql"
    migration_file.write_text("CREATE TABLE test_table (id INTEGER PRIMARY KEY);")

    # Apply it
    apply_migration(conn, migration_file)

    # Check table was created
    result = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
    assert result is not None

    # Check migration was recorded
    applied = get_applied_migrations(conn)
    assert "001_create_test.sql" in applied


def test_migrations_idempotent():
    """Test that migrations can be run multiple times safely."""
    conn = get_connection(":memory:")
    ensure_migrations_table(conn)

    # Running ensure_migrations_table multiple times should not error
    ensure_migrations_table(conn)
    ensure_migrations_table(conn)


def test_full_migration_workflow():
    """Test the full migration workflow with real schema."""
    # This will apply the real migrations
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/migrate.py", "--db-path", ":memory:"],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Successfully applied" in result.stdout or "No pending migrations" in result.stdout
