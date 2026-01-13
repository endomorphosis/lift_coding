"""Tests for GitHub connections persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.github_connections import (
    create_github_connection,
    delete_github_connection,
    get_github_connection,
    get_github_connections_by_user,
    update_github_connection,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))


class TestGitHubConnectionCreation:
    """Test GitHub connection creation."""

    def test_create_basic_connection(self, db_conn, test_user_id):
        """Test creating a basic GitHub connection."""
        conn = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
            token_ref="secret://tokens/github/user123",
            scopes="repo,read:org",
        )

        assert conn.id is not None
        assert conn.user_id == test_user_id
        assert conn.installation_id == 12345
        assert conn.token_ref == "secret://tokens/github/user123"
        assert conn.scopes == "repo,read:org"
        assert conn.created_at is not None
        assert conn.updated_at is not None

    def test_create_minimal_connection(self, db_conn, test_user_id):
        """Test creating a connection with minimal fields."""
        conn = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
        )

        assert conn.id is not None
        assert conn.user_id == test_user_id
        assert conn.installation_id is None
        assert conn.token_ref is None
        assert conn.scopes is None


class TestGitHubConnectionRetrieval:
    """Test GitHub connection retrieval."""

    def test_get_connection_by_id(self, db_conn, test_user_id):
        """Test retrieving a connection by ID."""
        created = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
            token_ref="secret://tokens/github/user123",
            scopes="repo",
        )

        retrieved = get_github_connection(db_conn, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.user_id == test_user_id
        assert retrieved.installation_id == 12345
        assert retrieved.token_ref == "secret://tokens/github/user123"
        assert retrieved.scopes == "repo"

    def test_get_connection_not_found(self, db_conn):
        """Test retrieving a non-existent connection."""
        result = get_github_connection(db_conn, str(uuid.uuid4()))
        assert result is None

    def test_get_connections_by_user(self, db_conn, test_user_id, test_user_id_2):
        """Test retrieving all connections for a user."""
        # Create connections for user 1
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=11111,
        )
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=22222,
        )

        # Create connection for user 2
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id_2,
            installation_id=33333,
        )

        # Retrieve connections for user 1
        user1_connections = get_github_connections_by_user(db_conn, test_user_id)
        assert len(user1_connections) == 2
        assert {c.installation_id for c in user1_connections} == {11111, 22222}

        # Retrieve connections for user 2
        user2_connections = get_github_connections_by_user(db_conn, test_user_id_2)
        assert len(user2_connections) == 1
        assert user2_connections[0].installation_id == 33333

    def test_get_connections_by_user_empty(self, db_conn, test_user_id):
        """Test retrieving connections for user with no connections."""
        connections = get_github_connections_by_user(db_conn, test_user_id)
        assert len(connections) == 0


class TestGitHubConnectionUpdate:
    """Test GitHub connection updates."""

    def test_update_connection(self, db_conn, test_user_id):
        """Test updating a connection."""
        conn = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
            token_ref="old_ref",
            scopes="repo",
        )

        # Update the connection
        updated = update_github_connection(
            db_conn,
            conn.id,
            installation_id=99999,
            token_ref="new_ref",
            scopes="repo,read:org",
        )

        assert updated is not None
        assert updated.id == conn.id
        assert updated.installation_id == 99999
        assert updated.token_ref == "new_ref"
        assert updated.scopes == "repo,read:org"
        assert updated.updated_at > conn.updated_at

    def test_update_partial_fields(self, db_conn, test_user_id):
        """Test updating only some fields."""
        conn = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
            token_ref="old_ref",
            scopes="repo",
        )

        # Update only token_ref
        updated = update_github_connection(
            db_conn,
            conn.id,
            token_ref="new_ref",
        )

        assert updated is not None
        assert updated.installation_id == 12345  # Unchanged
        assert updated.token_ref == "new_ref"  # Changed
        assert updated.scopes == "repo"  # Unchanged

    def test_update_connection_not_found(self, db_conn):
        """Test updating a non-existent connection."""
        result = update_github_connection(
            db_conn,
            str(uuid.uuid4()),
            installation_id=12345,
        )
        assert result is None


class TestGitHubConnectionDeletion:
    """Test GitHub connection deletion."""

    def test_delete_connection(self, db_conn, test_user_id):
        """Test deleting a connection."""
        conn = create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Delete the connection
        deleted = delete_github_connection(db_conn, conn.id)
        assert deleted is True

        # Verify it's gone
        retrieved = get_github_connection(db_conn, conn.id)
        assert retrieved is None

    def test_delete_connection_not_found(self, db_conn):
        """Test deleting a non-existent connection."""
        deleted = delete_github_connection(db_conn, str(uuid.uuid4()))
        assert deleted is False
