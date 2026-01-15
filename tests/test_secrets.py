"""Tests for secret management functionality."""

import os

from handsfree.secrets import EnvSecretManager, SecretManager


class TestEnvSecretManager:
    """Tests for EnvSecretManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = EnvSecretManager(prefix="TEST_SECRET_")
        # Clean up any existing test secrets
        for key in list(os.environ.keys()):
            if key.startswith("TEST_SECRET_"):
                del os.environ[key]

    def teardown_method(self):
        """Clean up after tests."""
        # Remove test secrets from environment
        for key in list(os.environ.keys()):
            if key.startswith("TEST_SECRET_"):
                del os.environ[key]

    def test_store_and_retrieve_secret(self):
        """Test storing and retrieving a secret."""
        secret_value = "ghp_test_token_12345"
        reference = self.manager.store_secret("github_token_user_123", secret_value)

        assert reference.startswith("env://TEST_SECRET_")

        retrieved = self.manager.get_secret(reference)
        assert retrieved == secret_value

    def test_store_secret_with_metadata(self):
        """Test storing a secret with metadata (metadata is ignored)."""
        secret_value = "ghp_test_token_12345"
        metadata = {"scopes": "repo,user", "expires_at": "2026-12-31"}

        reference = self.manager.store_secret("github_token_user_123", secret_value, metadata)
        retrieved = self.manager.get_secret(reference)

        assert retrieved == secret_value

    def test_get_nonexistent_secret(self):
        """Test retrieving a non-existent secret returns None."""
        result = self.manager.get_secret("env://TEST_SECRET_NONEXISTENT")
        assert result is None

    def test_update_secret(self):
        """Test updating an existing secret."""
        old_value = "ghp_old_token"
        new_value = "ghp_new_token"

        reference = self.manager.store_secret("github_token_user_123", old_value)

        # Update the secret
        success = self.manager.update_secret(reference, new_value)
        assert success is True

        # Verify the new value
        retrieved = self.manager.get_secret(reference)
        assert retrieved == new_value

    def test_update_nonexistent_secret(self):
        """Test updating a non-existent secret returns False."""
        success = self.manager.update_secret("env://TEST_SECRET_NONEXISTENT", "new_value")
        assert success is False

    def test_delete_secret(self):
        """Test deleting a secret."""
        secret_value = "ghp_test_token_12345"
        reference = self.manager.store_secret("github_token_user_123", secret_value)

        # Delete the secret
        success = self.manager.delete_secret(reference)
        assert success is True

        # Verify it's gone
        retrieved = self.manager.get_secret(reference)
        assert retrieved is None

    def test_delete_nonexistent_secret(self):
        """Test deleting a non-existent secret returns False."""
        success = self.manager.delete_secret("env://TEST_SECRET_NONEXISTENT")
        assert success is False

    def test_list_secrets(self):
        """Test listing all secrets."""
        # Store multiple secrets
        self.manager.store_secret("github_token_user_1", "token1")
        self.manager.store_secret("github_token_user_2", "token2")
        self.manager.store_secret("slack_token_user_1", "token3")

        # List all secrets
        all_refs = self.manager.list_secrets()
        assert len(all_refs) == 3

        # List secrets with prefix
        github_refs = self.manager.list_secrets(prefix="github_token_")
        assert len(github_refs) == 2

    def test_list_secrets_empty(self):
        """Test listing secrets when none exist."""
        refs = self.manager.list_secrets()
        assert len(refs) == 0

    def test_invalid_reference_format(self):
        """Test handling of invalid reference format."""
        # Missing "env://" prefix
        result = self.manager.get_secret("INVALID_FORMAT")
        assert result is None

        success = self.manager.delete_secret("INVALID_FORMAT")
        assert success is False

        success = self.manager.update_secret("INVALID_FORMAT", "new_value")
        assert success is False

    def test_key_normalization(self):
        """Test that keys are normalized to environment variable format."""
        # Keys with special characters should be normalized to the same key
        reference1 = self.manager.store_secret("github.token-user/123", "token1")
        reference2 = self.manager.store_secret("github_token_user_123", "token2")

        # Both keys normalize to the same env var, so the second overwrites the first
        # This is expected behavior - special characters are normalized
        assert self.manager.get_secret(reference1) == "token2"
        assert self.manager.get_secret(reference2) == "token2"

    def test_multiple_managers_share_environment(self):
        """Test that multiple manager instances can access the same secrets."""
        manager1 = EnvSecretManager(prefix="TEST_SECRET_")
        manager2 = EnvSecretManager(prefix="TEST_SECRET_")

        # Store with manager1
        reference = manager1.store_secret("shared_secret", "shared_value")

        # Retrieve with manager2
        retrieved = manager2.get_secret(reference)
        assert retrieved == "shared_value"

    def test_different_prefixes_are_isolated(self):
        """Test that different prefixes create isolated namespaces."""
        manager_a = EnvSecretManager(prefix="PREFIX_A_")
        manager_b = EnvSecretManager(prefix="PREFIX_B_")

        ref_a = manager_a.store_secret("secret1", "value_a")
        ref_b = manager_b.store_secret("secret1", "value_b")

        # Each manager should see only its own secret
        assert manager_a.get_secret(ref_a) == "value_a"
        assert manager_b.get_secret(ref_b) == "value_b"

        # List should show only own secrets
        refs_a = manager_a.list_secrets()
        refs_b = manager_b.list_secrets()

        assert len(refs_a) == 1
        assert len(refs_b) == 1
        assert refs_a[0] != refs_b[0]


class TestSecretManagerInterface:
    """Tests for SecretManager interface compliance."""

    def test_env_manager_implements_interface(self):
        """Test that EnvSecretManager implements SecretManager interface."""
        manager = EnvSecretManager()
        assert isinstance(manager, SecretManager)

        # Check that all required methods exist
        assert hasattr(manager, "store_secret")
        assert hasattr(manager, "get_secret")
        assert hasattr(manager, "delete_secret")
        assert hasattr(manager, "update_secret")
        assert hasattr(manager, "list_secrets")
