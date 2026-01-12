"""Shared test fixtures for persistence tests."""

from pathlib import Path
from uuid import uuid4

import pytest

from scripts.migrate import ensure_migrations_table
from src.handsfree.persistence import get_connection


@pytest.fixture
def db_conn():
    """Create an in-memory database with schema applied and a test user."""
    conn = get_connection(":memory:")
    ensure_migrations_table(conn)

    # Apply the initial schema migration
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    migration_file = migrations_dir / "001_initial_schema.sql"
    sql_content = migration_file.read_text()
    conn.execute(sql_content)

    return conn


@pytest.fixture
def test_user_id(db_conn):
    """Create a test user and return its ID."""
    user_id = uuid4()
    db_conn.execute(
        "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)",
        [str(user_id), f"test-{user_id}@example.com", "Test User"],
    )
    return user_id


def create_test_user(db_conn, email=None):
    """Helper function to create a test user."""
    user_id = uuid4()
    if email is None:
        email = f"test-{user_id}@example.com"
    db_conn.execute(
        "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)",
        [str(user_id), email, "Test User"],
    )
    return user_id
