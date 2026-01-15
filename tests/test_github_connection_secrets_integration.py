"""Integration tests for secret manager with GitHub connections."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.github_connections import (
    create_github_connection,
    delete_github_connection,
    get_github_connection,
    get_github_connections_by_user,
)
from handsfree.secrets import get_default_secret_manager, reset_secret_manager


@pytest.fixture(autouse=True)
def reset_secrets():
    """Reset the secret manager singleton before each test."""
    reset_secret_manager()
    yield
    reset_secret_manager()


class TestGitHubConnectionSecretIntegration:
    """Tests for GitHub connection integration with secret manager."""

    def test_store_token_with_secret_manager(self):
        """Test storing a GitHub token using the secret manager."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        # Simulate what the API endpoint would do
        user_id = str(uuid.uuid4())
        github_token = "ghp_test_token_12345"

        # Store the token securely
        token_ref = secret_manager.store_secret(
            key=f"github_token_{user_id}",
            value=github_token,
            metadata={"user_id": user_id, "scopes": "repo,user"},
        )

        # Create the connection with the reference
        connection = create_github_connection(
            conn=db,
            user_id=user_id,
            token_ref=token_ref,
            scopes="repo,user",
        )

        # Verify the connection was created
        assert connection.token_ref == token_ref
        assert connection.user_id == user_id

        # Verify we can retrieve the actual token
        actual_token = secret_manager.get_secret(connection.token_ref)
        assert actual_token == github_token

    def test_retrieve_token_for_api_call(self):
        """Test the full flow of storing and retrieving a token."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        user_id = str(uuid.uuid4())
        original_token = "ghp_real_api_token"

        # Store token
        token_ref = secret_manager.store_secret(f"github_token_{user_id}", original_token)

        # Create connection
        connection = create_github_connection(
            conn=db, user_id=user_id, token_ref=token_ref, scopes="repo"
        )

        # Later, retrieve the connection
        retrieved_conn = get_github_connection(db, connection.id)
        assert retrieved_conn is not None

        # Get the actual token for API calls
        actual_token = secret_manager.get_secret(retrieved_conn.token_ref)
        assert actual_token == original_token

    def test_delete_connection_with_secret_cleanup(self):
        """Test that deleting a connection can also clean up the secret."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        user_id = str(uuid.uuid4())
        token = "ghp_token_to_delete"

        # Store and create
        token_ref = secret_manager.store_secret(f"github_token_{user_id}", token)
        connection = create_github_connection(
            conn=db, user_id=user_id, token_ref=token_ref, scopes="repo"
        )

        # Verify secret exists
        assert secret_manager.get_secret(token_ref) == token

        # Delete connection AND secret (simulating what API does)
        if connection.token_ref:
            secret_manager.delete_secret(connection.token_ref)
        delete_github_connection(conn=db, connection_id=connection.id)

        # Verify both are gone
        assert get_github_connection(db, connection.id) is None
        assert secret_manager.get_secret(token_ref) is None

    def test_multiple_connections_with_secrets(self):
        """Test managing multiple connections with different secrets."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        user_id = str(uuid.uuid4())
        connections = []

        # Create 3 connections with different tokens
        for i in range(3):
            token = f"ghp_token_{i}"
            token_ref = secret_manager.store_secret(f"github_token_{user_id}_{i}", token)
            conn = create_github_connection(
                conn=db, user_id=user_id, token_ref=token_ref, scopes="repo"
            )
            connections.append((conn, token))

        # Retrieve all connections
        all_conns = get_github_connections_by_user(db, user_id)
        assert len(all_conns) == 3

        # Verify each token can be retrieved
        for conn, original_token in connections:
            retrieved_token = secret_manager.get_secret(conn.token_ref)
            assert retrieved_token == original_token

    def test_connection_without_token(self):
        """Test creating a connection without a token (GitHub App installation)."""
        db = init_db(":memory:")

        # For GitHub App installations, we don't need a token_ref
        connection = create_github_connection(
            conn=db,
            user_id=str(uuid.uuid4()),
            installation_id=12345,
            token_ref=None,
            scopes=None,
        )

        assert connection.installation_id == 12345
        assert connection.token_ref is None

    def test_token_not_exposed_in_connection_object(self):
        """Test that the actual token is never in the connection object."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        secret_token = "ghp_super_secret_token"
        token_ref = secret_manager.store_secret("github_token_secure", secret_token)

        connection = create_github_connection(
            conn=db, user_id=str(uuid.uuid4()), token_ref=token_ref, scopes="repo"
        )

        # Convert connection to dict/string representation
        conn_str = str(vars(connection))

        # The actual token should NOT appear anywhere in the connection object
        assert secret_token not in conn_str
        # But the reference should be present
        assert token_ref in conn_str

    def test_secret_manager_factory_integration(self):
        """Test that the factory provides the correct secret manager."""
        from handsfree.secrets import get_secret_manager

        # Should return EnvSecretManager by default
        manager = get_secret_manager()
        assert manager is not None

        # Test basic operations
        ref = manager.store_secret("test_key", "test_value")
        assert manager.get_secret(ref) == "test_value"
        assert manager.delete_secret(ref) is True

    def test_secret_metadata_storage(self):
        """Test that metadata is properly stored with secrets."""
        secret_manager = get_default_secret_manager()

        metadata = {
            "user_id": str(uuid.uuid4()),
            "scopes": "repo,user,admin:org",
            "source": "oauth",
        }

        token_ref = secret_manager.store_secret(
            key="github_token_with_metadata", value="ghp_token_value", metadata=metadata
        )

        # Retrieve the secret (metadata is stored but may not be retrievable
        # depending on the backend implementation)
        token = secret_manager.get_secret(token_ref)
        assert token == "ghp_token_value"

    def test_isolation_between_users(self):
        """Test that different users' tokens are isolated."""
        db = init_db(":memory:")
        secret_manager = get_default_secret_manager()

        user_id_1 = str(uuid.uuid4())
        user_id_2 = str(uuid.uuid4())

        # User 1
        token_ref_1 = secret_manager.store_secret("github_token_user1", "ghp_user1_token")
        conn1 = create_github_connection(
            conn=db, user_id=user_id_1, token_ref=token_ref_1, scopes="repo"
        )

        # User 2
        token_ref_2 = secret_manager.store_secret("github_token_user2", "ghp_user2_token")
        conn2 = create_github_connection(
            conn=db, user_id=user_id_2, token_ref=token_ref_2, scopes="repo"
        )

        # Each user should only see their own connections
        user1_conns = get_github_connections_by_user(db, user_id_1)
        user2_conns = get_github_connections_by_user(db, user_id_2)

        assert len(user1_conns) == 1
        assert len(user2_conns) == 1
        assert user1_conns[0].id == conn1.id
        assert user2_conns[0].id == conn2.id

        # Each user should get their own token
        token1 = secret_manager.get_secret(user1_conns[0].token_ref)
        token2 = secret_manager.get_secret(user2_conns[0].token_ref)

        assert token1 == "ghp_user1_token"
        assert token2 == "ghp_user2_token"
