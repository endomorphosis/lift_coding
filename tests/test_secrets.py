"""Tests for secret management functionality."""

import os
from unittest.mock import Mock, patch

import pytest
from google.api_core.exceptions import NotFound, GoogleAPIError
from hvac.exceptions import InvalidPath, VaultError

from handsfree.secrets import EnvSecretManager, GCPSecretManager, SecretManager, VaultSecretManager


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


class TestVaultSecretManager:
    """Tests for VaultSecretManager."""

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_initialization_with_token(self, mock_client_class):
        """Test VaultSecretManager initialization with token authentication."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
            vault_mount="secret",
        )

        mock_client_class.assert_called_once_with(
            url="https://vault.example.com",
            namespace=None,
        )
        assert mock_client.token == "test-token"

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_initialization_with_approle(self, mock_client_class):
        """Test VaultSecretManager initialization with AppRole authentication."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.auth.approle.login.return_value = {"auth": {"client_token": "approle-token"}}
        mock_client_class.return_value = mock_client

        VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_role_id="test-role-id",
            vault_secret_id="test-secret-id",
        )

        mock_client.auth.approle.login.assert_called_once_with(
            role_id="test-role-id",
            secret_id="test-secret-id",
        )
        assert mock_client.token == "approle-token"

    def test_initialization_missing_addr(self):
        """Test that initialization fails without VAULT_ADDR."""
        with pytest.raises(ValueError, match="VAULT_ADDR"):
            VaultSecretManager(vault_token="test-token")

    def test_initialization_missing_auth(self):
        """Test that initialization fails without authentication credentials."""
        with pytest.raises(ValueError, match="VAULT_TOKEN or both VAULT_ROLE_ID"):
            VaultSecretManager(vault_addr="https://vault.example.com")

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_initialization_authentication_failure(self, mock_client_class):
        """Test that initialization fails if authentication fails."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = False
        mock_client_class.return_value = mock_client

        with pytest.raises(VaultError, match="Failed to authenticate"):
            VaultSecretManager(
                vault_addr="https://vault.example.com",
                vault_token="bad-token",
            )

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_store_and_retrieve_secret(self, mock_client_class):
        """Test storing and retrieving a secret."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        # Mock the store response
        mock_client.secrets.kv.v2.create_or_update_secret.return_value = None

        # Mock the retrieve response
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "ghp_test_token_12345"}}
        }

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        # Store secret
        secret_value = "ghp_test_token_12345"
        reference = manager.store_secret("github_token_user_123", secret_value)

        assert reference == "vault://github_token_user_123"
        mock_client.secrets.kv.v2.create_or_update_secret.assert_called_once()

        # Retrieve secret
        retrieved = manager.get_secret(reference)
        assert retrieved == secret_value

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_store_secret_with_metadata(self, mock_client_class):
        """Test storing a secret with metadata."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        secret_value = "ghp_test_token_12345"
        metadata = {"scopes": "repo,user", "expires_at": "2026-12-31"}

        manager.store_secret("github_token_user_123", secret_value, metadata)

        # Verify the call included metadata
        call_args = mock_client.secrets.kv.v2.create_or_update_secret.call_args
        assert call_args[1]["secret"]["value"] == secret_value
        assert call_args[1]["secret"]["metadata"] == metadata

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_get_nonexistent_secret(self, mock_client_class):
        """Test retrieving a non-existent secret returns None."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        result = manager.get_secret("vault://nonexistent_secret")
        assert result is None

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_update_secret(self, mock_client_class):
        """Test updating an existing secret."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        # Mock that secret exists
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "old_value"}}
        }

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        # Update the secret
        success = manager.update_secret("vault://test_secret", "new_value")
        assert success is True

        # Verify update was called
        assert mock_client.secrets.kv.v2.create_or_update_secret.called

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_update_nonexistent_secret(self, mock_client_class):
        """Test updating a non-existent secret returns False."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        success = manager.update_secret("vault://nonexistent_secret", "new_value")
        assert success is False

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_delete_secret(self, mock_client_class):
        """Test deleting a secret."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        # Delete the secret
        success = manager.delete_secret("vault://test_secret")
        assert success is True

        # Verify delete was called
        mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_delete_nonexistent_secret(self, mock_client_class):
        """Test deleting a non-existent secret returns False."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = InvalidPath()
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        success = manager.delete_secret("vault://nonexistent_secret")
        assert success is False

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_list_secrets(self, mock_client_class):
        """Test listing all secrets."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        # Mock list response with flat secrets
        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["secret1", "secret2", "secret3"]}
        }

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        refs = manager.list_secrets()
        assert len(refs) == 3
        assert "vault://secret1" in refs
        assert "vault://secret2" in refs
        assert "vault://secret3" in refs

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_list_secrets_with_prefix(self, mock_client_class):
        """Test listing secrets with a prefix filter."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        # Mock list response
        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["token1", "token2"]}
        }

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        refs = manager.list_secrets(prefix="github_token")
        assert len(refs) == 2

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_list_secrets_empty(self, mock_client_class):
        """Test listing secrets when none exist."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.list_secrets.side_effect = InvalidPath()
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        refs = manager.list_secrets()
        assert len(refs) == 0

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_invalid_reference_format(self, mock_client_class):
        """Test handling of invalid reference format."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        # Missing "vault://" prefix
        result = manager.get_secret("INVALID_FORMAT")
        assert result is None

        success = manager.delete_secret("INVALID_FORMAT")
        assert success is False

        success = manager.update_secret("INVALID_FORMAT", "new_value")
        assert success is False

    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_vault_manager_implements_interface(self, mock_client_class):
        """Test that VaultSecretManager implements SecretManager interface."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager(
            vault_addr="https://vault.example.com",
            vault_token="test-token",
        )

        assert isinstance(manager, SecretManager)

        # Check that all required methods exist
        assert hasattr(manager, "store_secret")
        assert hasattr(manager, "get_secret")
        assert hasattr(manager, "delete_secret")
        assert hasattr(manager, "update_secret")
        assert hasattr(manager, "list_secrets")

    @patch.dict(
        os.environ,
        {
            "VAULT_ADDR": "https://vault.example.com",
            "VAULT_TOKEN": "env-token",
            "VAULT_MOUNT": "custom-mount",
            "VAULT_NAMESPACE": "test-namespace",
        },
    )
    @patch("handsfree.secrets.vault_secrets.hvac.Client")
    def test_initialization_from_environment(self, mock_client_class):
        """Test that VaultSecretManager can be initialized from environment variables."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client_class.return_value = mock_client

        manager = VaultSecretManager()

        assert manager.vault_addr == "https://vault.example.com"
        assert manager.vault_token == "env-token"
        assert manager.vault_mount == "custom-mount"
        assert manager.vault_namespace == "test-namespace"

        mock_client_class.assert_called_once_with(
            url="https://vault.example.com",
            namespace="test-namespace",
        )


class TestGCPSecretManager:
    """Tests for GCPSecretManager."""

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_initialization(self, mock_client_class):
        """Test GCPSecretManager initialization."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(
            project_id="test-project",
            prefix="testprefix",
        )

        assert manager.project_id == "test-project"
        assert manager.prefix == "testprefix"
        mock_client_class.assert_called_once()

    def test_initialization_missing_project_id(self):
        """Test that initialization fails without project ID."""
        with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"):
            GCPSecretManager()

    @patch.dict(
        os.environ,
        {
            "GOOGLE_CLOUD_PROJECT": "env-project",
            "HANDSFREE_GCP_SECRETS_PREFIX": "env-prefix",
        },
    )
    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_initialization_from_environment(self, mock_client_class):
        """Test that GCPSecretManager can be initialized from environment variables."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager()

        assert manager.project_id == "env-project"
        assert manager.prefix == "env-prefix"

    @patch.dict(
        os.environ,
        {
            "GCP_PROJECT_ID": "alt-project",
        },
    )
    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_initialization_gcp_project_id_env(self, mock_client_class):
        """Test that GCP_PROJECT_ID environment variable works."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager()

        assert manager.project_id == "alt-project"

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_store_and_retrieve_secret(self, mock_client_class):
        """Test storing and retrieving a secret."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock the create secret response
        mock_client.create_secret.return_value = Mock()

        # Mock the add version response
        mock_client.add_secret_version.return_value = Mock()

        # Mock the access version response
        mock_payload = Mock()
        mock_payload.data = b"ghp_test_token_12345"
        mock_response = Mock()
        mock_response.payload = mock_payload
        mock_client.access_secret_version.return_value = mock_response

        manager = GCPSecretManager(project_id="test-project")

        # Store secret
        secret_value = "ghp_test_token_12345"
        reference = manager.store_secret("github_token_user_123", secret_value)

        assert reference.startswith("gcp://")
        assert "handsfree-github-token-user-123" in reference

        # Verify create_secret was called
        mock_client.create_secret.assert_called_once()
        call_args = mock_client.create_secret.call_args[1]
        assert call_args["request"]["parent"] == "projects/test-project"
        assert call_args["request"]["secret_id"] == "handsfree-github-token-user-123"

        # Verify add_secret_version was called
        mock_client.add_secret_version.assert_called_once()
        version_call_args = mock_client.add_secret_version.call_args[1]
        assert version_call_args["request"]["payload"]["data"] == b"ghp_test_token_12345"

        # Retrieve secret
        retrieved = manager.get_secret(reference)
        assert retrieved == secret_value

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_store_secret_with_metadata(self, mock_client_class):
        """Test storing a secret with metadata."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        secret_value = "ghp_test_token_12345"
        metadata = {"scopes": "repo,user", "expires_at": "2026-12-31"}

        manager.store_secret("github_token_user_123", secret_value, metadata)

        # Verify the call included labels
        call_args = mock_client.create_secret.call_args[1]
        assert "labels" in call_args["request"]["secret"]
        labels = call_args["request"]["secret"]["labels"]
        assert "scopes" in labels
        assert "expires-at" in labels

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_store_secret_already_exists(self, mock_client_class):
        """Test storing a secret that already exists."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock that secret already exists
        mock_client.create_secret.side_effect = GoogleAPIError("already exists")

        manager = GCPSecretManager(project_id="test-project")

        # Should not raise, just add new version
        reference = manager.store_secret("existing_secret", "new_value")

        assert reference.startswith("gcp://")
        # Verify add_secret_version was still called
        mock_client.add_secret_version.assert_called_once()

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_get_nonexistent_secret(self, mock_client_class):
        """Test retrieving a non-existent secret returns None."""
        mock_client = Mock()
        mock_client.access_secret_version.side_effect = NotFound("secret not found")
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        result = manager.get_secret("gcp://nonexistent-secret")
        assert result is None

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_update_secret(self, mock_client_class):
        """Test updating an existing secret."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock that secret exists
        mock_client.get_secret.return_value = Mock()

        manager = GCPSecretManager(project_id="test-project")

        # Update the secret
        success = manager.update_secret("gcp://test-secret", "new_value")
        assert success is True

        # Verify add_secret_version was called with new value
        mock_client.add_secret_version.assert_called_once()
        call_args = mock_client.add_secret_version.call_args[1]
        assert call_args["request"]["payload"]["data"] == b"new_value"

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_update_secret_with_metadata(self, mock_client_class):
        """Test updating a secret with new metadata."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock that secret exists
        mock_client.get_secret.return_value = Mock()

        manager = GCPSecretManager(project_id="test-project")

        metadata = {"updated": "true"}
        success = manager.update_secret("gcp://test-secret", "new_value", metadata)
        assert success is True

        # Verify update_secret was called to update labels
        mock_client.update_secret.assert_called_once()
        call_args = mock_client.update_secret.call_args[1]
        assert "labels" in call_args["request"]["secret"]

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_update_nonexistent_secret(self, mock_client_class):
        """Test updating a non-existent secret returns False."""
        mock_client = Mock()
        mock_client.get_secret.side_effect = NotFound("secret not found")
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        success = manager.update_secret("gcp://nonexistent-secret", "new_value")
        assert success is False

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_delete_secret(self, mock_client_class):
        """Test deleting a secret."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        # Delete the secret
        success = manager.delete_secret("gcp://test-secret")
        assert success is True

        # Verify delete_secret was called
        mock_client.delete_secret.assert_called_once()
        call_args = mock_client.delete_secret.call_args[1]
        assert "projects/test-project/secrets/test-secret" in call_args["request"]["name"]

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_delete_nonexistent_secret(self, mock_client_class):
        """Test deleting a non-existent secret returns False."""
        mock_client = Mock()
        mock_client.delete_secret.side_effect = NotFound("secret not found")
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        success = manager.delete_secret("gcp://nonexistent-secret")
        assert success is False

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_list_secrets(self, mock_client_class):
        """Test listing all secrets."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock list response
        mock_secret1 = Mock()
        mock_secret1.name = "projects/test-project/secrets/handsfree-secret1"
        mock_secret2 = Mock()
        mock_secret2.name = "projects/test-project/secrets/handsfree-secret2"
        mock_secret3 = Mock()
        mock_secret3.name = "projects/test-project/secrets/other-secret3"
        
        mock_secrets = [mock_secret1, mock_secret2, mock_secret3]
        mock_client.list_secrets.return_value = mock_secrets

        manager = GCPSecretManager(project_id="test-project")

        refs = manager.list_secrets()
        # Should only include secrets with handsfree prefix
        assert len(refs) == 2
        assert "gcp://handsfree-secret1" in refs
        assert "gcp://handsfree-secret2" in refs
        assert "gcp://other-secret3" not in refs

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_list_secrets_with_prefix(self, mock_client_class):
        """Test listing secrets with a prefix filter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock list response
        mock_secret1 = Mock()
        mock_secret1.name = "projects/test-project/secrets/handsfree-github-token-1"
        mock_secret2 = Mock()
        mock_secret2.name = "projects/test-project/secrets/handsfree-github-token-2"
        mock_secret3 = Mock()
        mock_secret3.name = "projects/test-project/secrets/handsfree-slack-token-1"
        
        mock_secrets = [mock_secret1, mock_secret2, mock_secret3]
        mock_client.list_secrets.return_value = mock_secrets

        manager = GCPSecretManager(project_id="test-project")

        refs = manager.list_secrets(prefix="github_token")
        assert len(refs) == 2
        assert all("github-token" in ref for ref in refs)

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_list_secrets_empty(self, mock_client_class):
        """Test listing secrets when none exist."""
        mock_client = Mock()
        mock_client.list_secrets.return_value = []
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        refs = manager.list_secrets()
        assert len(refs) == 0

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_invalid_reference_format(self, mock_client_class):
        """Test handling of invalid reference format."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        # Missing "gcp://" prefix
        result = manager.get_secret("INVALID_FORMAT")
        assert result is None

        success = manager.delete_secret("INVALID_FORMAT")
        assert success is False

        success = manager.update_secret("INVALID_FORMAT", "new_value")
        assert success is False

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_gcp_manager_implements_interface(self, mock_client_class):
        """Test that GCPSecretManager implements SecretManager interface."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        assert isinstance(manager, SecretManager)

        # Check that all required methods exist
        assert hasattr(manager, "store_secret")
        assert hasattr(manager, "get_secret")
        assert hasattr(manager, "delete_secret")
        assert hasattr(manager, "update_secret")
        assert hasattr(manager, "list_secrets")

    @patch("handsfree.secrets.gcp_secrets.secretmanager.SecretManagerServiceClient")
    def test_key_normalization(self, mock_client_class):
        """Test that keys are normalized to GCP secret name format."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        manager = GCPSecretManager(project_id="test-project")

        # Keys with special characters should be normalized
        reference = manager.store_secret("github.token_user/123", "token")

        # Should normalize to lowercase with hyphens
        assert "handsfree-github-token-user-123" in reference
