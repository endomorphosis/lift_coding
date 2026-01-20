"""Tests for secret management functionality."""

import os
from unittest.mock import Mock, patch

import pytest
from hvac.exceptions import InvalidPath, VaultError

from handsfree.secrets import AWSSecretManager, EnvSecretManager, SecretManager, VaultSecretManager


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


class TestAWSSecretManager:
    """Tests for AWSSecretManager."""

    @pytest.fixture
    def mock_boto3_client(self):
        """Create a mock boto3 client."""
        mock_client = Mock()
        return mock_client

    @pytest.fixture
    def mock_boto3_module(self, mock_boto3_client):
        """Create a mock boto3 module."""
        mock_boto3 = Mock()
        mock_boto3.client.return_value = mock_boto3_client
        return mock_boto3

    def test_initialization_requires_region(self, mock_boto3_client):
        """Test that initialization fails without AWS region configured."""
        with patch.dict(os.environ, {}, clear=True):
            from handsfree.secrets import AWSSecretManager

            with pytest.raises(ValueError, match="AWS region is required"):
                AWSSecretManager(boto3_client=mock_boto3_client)

    def test_initialization_with_region_parameter(self, mock_boto3_client):
        """Test AWSSecretManager initialization with region parameter."""

        manager = AWSSecretManager(
            region="us-west-2", prefix="test/", boto3_client=mock_boto3_client
        )

        assert manager.region == "us-west-2"
        assert manager.prefix == "test/"
        assert manager.client == mock_boto3_client

    @patch.dict(os.environ, {"AWS_REGION": "us-east-1"})
    def test_initialization_from_environment(self, mock_boto3_client):
        """Test that AWSSecretManager can be initialized from environment variables."""

        manager = AWSSecretManager(boto3_client=mock_boto3_client)

        assert manager.region == "us-east-1"
        assert manager.prefix == "handsfree/"

    @patch.dict(
        os.environ, {"AWS_DEFAULT_REGION": "eu-west-1", "HANDSFREE_AWS_SECRETS_PREFIX": "myapp/"}
    )
    def test_initialization_with_custom_prefix(self, mock_boto3_client):
        """Test initialization with custom prefix from environment."""

        manager = AWSSecretManager(boto3_client=mock_boto3_client)

        assert manager.region == "eu-west-1"
        assert manager.prefix == "myapp/"

    def test_prefix_normalization(self, mock_boto3_client):
        """Test that prefix is normalized to end with /."""

        manager = AWSSecretManager(
            region="us-east-1", prefix="test", boto3_client=mock_boto3_client
        )

        assert manager.prefix == "test/"

    def test_store_and_retrieve_secret(self, mock_boto3_client):
        """Test storing and retrieving a secret."""

        # Mock create_secret response
        mock_boto3_client.create_secret.return_value = {"ARN": "arn:aws:secretsmanager:..."}

        # Mock get_secret_value response
        mock_boto3_client.get_secret_value.return_value = {
            "SecretString": '{"value": "ghp_test_token_12345"}'
        }

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        # Store secret
        secret_value = "ghp_test_token_12345"
        reference = manager.store_secret("github_token_user_123", secret_value)

        assert reference == "aws://test/github_token_user_123"
        mock_boto3_client.create_secret.assert_called_once()

        # Retrieve secret
        retrieved = manager.get_secret(reference)
        assert retrieved == secret_value
        mock_boto3_client.get_secret_value.assert_called_once_with(
            SecretId="test/github_token_user_123"
        )

    def test_store_secret_with_metadata(self, mock_boto3_client):
        """Test storing a secret with metadata (stored as tags)."""

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        secret_value = "ghp_test_token_12345"
        metadata = {"scopes": "repo,user", "expires_at": "2026-12-31"}

        manager.store_secret("github_token_user_123", secret_value, metadata)

        # Verify the call included tags
        call_args = mock_boto3_client.create_secret.call_args
        assert call_args[1]["Name"] == "test/github_token_user_123"
        assert call_args[1]["Tags"] == [
            {"Key": "scopes", "Value": "repo,user"},
            {"Key": "expires_at", "Value": "2026-12-31"},
        ]

    def test_store_secret_updates_existing(self, mock_boto3_client):
        """Test that storing an existing secret updates it."""

        # Mock ResourceExistsException
        from botocore.exceptions import ClientError

        mock_boto3_client.create_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceExistsException"}}, "CreateSecret"
        )
        mock_boto3_client.put_secret_value.return_value = {}

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        reference = manager.store_secret("existing_secret", "new_value")

        assert reference == "aws://test/existing_secret"
        mock_boto3_client.put_secret_value.assert_called_once()

    def test_get_nonexistent_secret(self, mock_boto3_client):
        """Test retrieving a non-existent secret returns None."""
        from botocore.exceptions import ClientError

        mock_boto3_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
        )

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        result = manager.get_secret("aws://test/nonexistent_secret")
        assert result is None

    def test_update_secret(self, mock_boto3_client):
        """Test updating an existing secret."""

        # Mock describe_secret (secret exists)
        mock_boto3_client.describe_secret.return_value = {"Name": "test/test_secret"}
        mock_boto3_client.put_secret_value.return_value = {}

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        # Update the secret
        success = manager.update_secret("aws://test/test_secret", "new_value")
        assert success is True

        mock_boto3_client.put_secret_value.assert_called_once()

    def test_update_nonexistent_secret(self, mock_boto3_client):
        """Test updating a non-existent secret returns False."""
        from botocore.exceptions import ClientError

        mock_boto3_client.put_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "PutSecretValue"
        )

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        success = manager.update_secret("aws://test/nonexistent_secret", "new_value")
        assert success is False

    def test_update_secret_with_metadata(self, mock_boto3_client):
        """Test updating a secret with new metadata."""

        mock_boto3_client.describe_secret.return_value = {"Name": "test/test_secret"}
        mock_boto3_client.put_secret_value.return_value = {}
        mock_boto3_client.tag_resource.return_value = {}

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        metadata = {"updated": "true"}
        success = manager.update_secret("aws://test/test_secret", "new_value", metadata)
        assert success is True

        mock_boto3_client.tag_resource.assert_called_once_with(
            SecretId="test/test_secret", Tags=[{"Key": "updated", "Value": "true"}]
        )

    def test_delete_secret(self, mock_boto3_client):
        """Test deleting a secret."""

        mock_boto3_client.delete_secret.return_value = {}

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client, force_delete=True
        )

        # Delete the secret
        success = manager.delete_secret("aws://test/test_secret")
        assert success is True

        mock_boto3_client.delete_secret.assert_called_once_with(
            SecretId="test/test_secret", ForceDeleteWithoutRecovery=True
        )

    def test_delete_nonexistent_secret(self, mock_boto3_client):
        """Test deleting a non-existent secret returns False."""
        from botocore.exceptions import ClientError

        mock_boto3_client.delete_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "DeleteSecret"
        )

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client, force_delete=True
        )

        success = manager.delete_secret("aws://test/nonexistent_secret")
        assert success is False

    def test_delete_secret_with_recovery_window(self, mock_boto3_client):
        """Test deleting a secret with recovery window (production mode)."""

        mock_boto3_client.delete_secret.return_value = {}

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client, force_delete=False
        )

        # Delete the secret
        success = manager.delete_secret("aws://test/test_secret")
        assert success is True

        # Should use recovery window instead of force delete
        mock_boto3_client.delete_secret.assert_called_once_with(
            SecretId="test/test_secret", RecoveryWindowInDays=30
        )

    def test_list_secrets(self, mock_boto3_client):
        """Test listing all secrets."""

        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "SecretList": [
                    {"Name": "test/secret1"},
                    {"Name": "test/secret2"},
                    {"Name": "test/secret3"},
                ]
            }
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        refs = manager.list_secrets()
        assert len(refs) == 3
        assert "aws://test/secret1" in refs
        assert "aws://test/secret2" in refs
        assert "aws://test/secret3" in refs
        # Verify all returned secrets match the manager's prefix
        for ref in refs:
            assert ref.startswith("aws://test/")

        # Verify that Filters parameter is used when prefix is set
        mock_paginator.paginate.assert_called_once_with(
            Filters=[{"Key": "name", "Values": ["test/"]}]
        )

    def test_list_secrets_with_prefix(self, mock_boto3_client):
        """Test listing secrets with a prefix filter."""

        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "SecretList": [
                    {"Name": "test/github_token1"},
                    {"Name": "test/github_token2"},
                ]
            }
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        refs = manager.list_secrets(prefix="github_")
        assert len(refs) == 2
        # Verify all returned secrets match the prefix
        for ref in refs:
            assert ref.startswith("aws://test/github_")

        # Verify that the Filters parameter was used for better performance
        mock_paginator.paginate.assert_called_once_with(
            Filters=[{"Key": "name", "Values": ["test/github_"]}]
        )

    def test_list_secrets_skips_deleted(self, mock_boto3_client):
        """Test that listing secrets skips secrets scheduled for deletion."""

        # Mock paginator with one deleted secret
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "SecretList": [
                    {"Name": "test/secret1"},
                    {"Name": "test/secret2", "DeletedDate": "2026-01-20T00:00:00Z"},
                    {"Name": "test/secret3"},
                ]
            }
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        refs = manager.list_secrets()
        assert len(refs) == 2
        assert "aws://test/secret1" in refs
        assert "aws://test/secret3" in refs
        assert "aws://test/secret2" not in refs

    def test_list_secrets_empty(self, mock_boto3_client):
        """Test listing secrets when none exist."""

        # Mock empty paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{"SecretList": []}]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        refs = manager.list_secrets()
        assert len(refs) == 0

    def test_invalid_reference_format(self, mock_boto3_client):
        """Test handling of invalid reference format."""

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        # Missing "aws://" prefix
        result = manager.get_secret("INVALID_FORMAT")
        assert result is None

        success = manager.delete_secret("INVALID_FORMAT")
        assert success is False

        success = manager.update_secret("INVALID_FORMAT", "new_value")
        assert success is False

    def test_aws_manager_implements_interface(self, mock_boto3_client):
        """Test that AWSSecretManager implements SecretManager interface."""

        manager = AWSSecretManager(
            region="us-east-1", prefix="test/", boto3_client=mock_boto3_client
        )

        assert isinstance(manager, SecretManager)

        # Check that all required methods exist
        assert hasattr(manager, "store_secret")
        assert hasattr(manager, "get_secret")
        assert hasattr(manager, "delete_secret")
        assert hasattr(manager, "update_secret")
        assert hasattr(manager, "list_secrets")

