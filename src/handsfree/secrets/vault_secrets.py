"""HashiCorp Vault-based secret manager.

This implementation provides production-ready secret storage using HashiCorp Vault.
It supports both token-based authentication (for development) and AppRole authentication
(recommended for production).
"""

import logging
import os

import hvac
from hvac.exceptions import InvalidPath, VaultError

from .interface import SecretManager

logger = logging.getLogger(__name__)


class VaultSecretManager(SecretManager):
    """Secret manager that stores secrets in HashiCorp Vault.

    This implementation is suitable for:
    - Production environments requiring secure secret storage
    - Multi-tenant deployments
    - Environments requiring audit logs for secret access
    - Secrets rotation workflows

    Configuration:
    - VAULT_ADDR: Vault server address (e.g., "https://vault.example.com:8200")
    - VAULT_TOKEN: Direct token authentication (development only)
    - VAULT_ROLE_ID + VAULT_SECRET_ID: AppRole authentication (production)
    - VAULT_MOUNT: KV secrets engine mount point (default: "secret")
    - VAULT_NAMESPACE: Vault namespace (optional, for Vault Enterprise)

    Security features:
    - Encryption at rest (handled by Vault)
    - Access audit logging (handled by Vault)
    - Token-based or AppRole authentication
    - TLS/HTTPS communication
    """

    def __init__(
        self,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        vault_role_id: str | None = None,
        vault_secret_id: str | None = None,
        vault_mount: str | None = None,
        vault_namespace: str | None = None,
    ):
        """Initialize the Vault secret manager.

        Args:
            vault_addr: Vault server address (default: from VAULT_ADDR env var)
            vault_token: Direct token for authentication (default: from VAULT_TOKEN env var)
            vault_role_id: AppRole role ID (default: from VAULT_ROLE_ID env var)
            vault_secret_id: AppRole secret ID (default: from VAULT_SECRET_ID env var)
            vault_mount: KV mount point (default: from VAULT_MOUNT env var or "secret")
            vault_namespace: Vault namespace (default: from VAULT_NAMESPACE env var)

        Raises:
            ValueError: If required configuration is missing or invalid
            VaultError: If connection to Vault fails
        """
        # Load configuration from environment variables or parameters
        self.vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.vault_role_id = vault_role_id or os.getenv("VAULT_ROLE_ID")
        self.vault_secret_id = vault_secret_id or os.getenv("VAULT_SECRET_ID")
        self.vault_mount = vault_mount or os.getenv("VAULT_MOUNT", "secret")
        self.vault_namespace = vault_namespace or os.getenv("VAULT_NAMESPACE")

        # Validate configuration
        self._validate_config()

        # Initialize Vault client
        self.client = self._initialize_client()

        logger.info(
            "Initialized VaultSecretManager with mount: %s, namespace: %s",
            self.vault_mount,
            self.vault_namespace or "default",
        )

    def _validate_config(self) -> None:
        """Validate the Vault configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.vault_addr:
            raise ValueError(
                "VAULT_ADDR environment variable or vault_addr parameter is required"
            )

        # Must have either token or AppRole credentials
        has_token = bool(self.vault_token)
        has_approle = bool(self.vault_role_id and self.vault_secret_id)

        if not has_token and not has_approle:
            raise ValueError(
                "Either VAULT_TOKEN or both VAULT_ROLE_ID and VAULT_SECRET_ID "
                "environment variables must be set"
            )

        if has_token and has_approle:
            logger.warning(
                "Both token and AppRole credentials provided. Using token authentication."
            )

    def _initialize_client(self) -> hvac.Client:
        """Initialize and authenticate the Vault client.

        Returns:
            Authenticated hvac.Client instance

        Raises:
            VaultError: If authentication fails
        """
        try:
            # Create client
            client = hvac.Client(
                url=self.vault_addr,
                namespace=self.vault_namespace,
            )

            # Authenticate
            if self.vault_token:
                client.token = self.vault_token
                logger.info("Using token authentication")
            else:
                # Use AppRole authentication
                response = client.auth.approle.login(
                    role_id=self.vault_role_id,
                    secret_id=self.vault_secret_id,
                )
                client.token = response["auth"]["client_token"]
                logger.info("Using AppRole authentication")

            # Verify authentication
            if not client.is_authenticated():
                raise VaultError("Failed to authenticate with Vault")

            return client

        except Exception as e:
            logger.error("Failed to initialize Vault client: %s", e)
            raise VaultError(f"Failed to initialize Vault client: {e}") from e

    def _normalize_key(self, key: str) -> str:
        """Normalize a secret key to a Vault path format.

        Args:
            key: Secret key (e.g., "github_token_user_123")

        Returns:
            Normalized path (e.g., "github/token/user/123")
        """
        return key.replace(".", "/").replace("_", "/")

    def _get_secret_path(self, key: str) -> str:
        """Convert a secret key to a Vault path.

        Args:
            key: Secret key (e.g., "github_token_user_123")

        Returns:
            Vault path (e.g., "secret/data/github_token_user_123" for KV v2)
        """
        normalized_key = self._normalize_key(key)
        return f"{self.vault_mount}/data/{normalized_key}"

    def _get_metadata_path(self, key: str) -> str:
        """Get the metadata path for a secret.

        Args:
            key: Secret key

        Returns:
            Vault metadata path
        """
        normalized_key = self._normalize_key(key)
        return f"{self.vault_mount}/metadata/{normalized_key}"

    def _parse_reference(self, reference: str) -> str:
        """Parse a reference to get the secret key.

        Args:
            reference: Reference string (format: "vault://secret_key")

        Returns:
            Secret key

        Raises:
            ValueError: If reference format is invalid
        """
        if not reference.startswith("vault://"):
            raise ValueError(f"Invalid reference format: {reference}")
        return reference[8:]  # Strip "vault://" prefix

    def store_secret(self, key: str, value: str, metadata: dict[str, str] | None = None) -> str:
        """Store a secret in Vault.

        Args:
            key: Unique identifier for the secret
            value: The secret value
            metadata: Optional metadata to store with the secret

        Returns:
            Reference string (format: "vault://secret_key")

        Raises:
            VaultError: If secret storage fails
        """
        try:
            # Prepare secret data
            secret_data = {"value": value}
            if metadata:
                secret_data["metadata"] = metadata

            # Store in Vault (KV v2)
            self.client.secrets.kv.v2.create_or_update_secret(
                path=self._normalize_key(key),
                secret=secret_data,
                mount_point=self.vault_mount,
            )

            logger.debug("Stored secret with key: %s", key)
            return f"vault://{key}"

        except Exception as e:
            logger.error("Failed to store secret: %s", e)
            raise VaultError(f"Failed to store secret: {e}") from e

    def get_secret(self, reference: str) -> str | None:
        """Retrieve a secret from Vault.

        Args:
            reference: The reference string

        Returns:
            The secret value, or None if not found

        Raises:
            VaultError: If secret retrieval fails (other than not found)
        """
        try:
            key = self._parse_reference(reference)

            # Read from Vault (KV v2)
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self._normalize_key(key),
                mount_point=self.vault_mount,
            )

            secret_data = response["data"]["data"]
            return secret_data.get("value")

        except InvalidPath:
            logger.warning("Secret not found: %s", reference)
            return None
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to retrieve secret: %s", e)
            raise VaultError(f"Failed to retrieve secret: {e}") from e

    def delete_secret(self, reference: str) -> bool:
        """Delete a secret from Vault.

        Args:
            reference: The reference to the secret

        Returns:
            True if deleted, False if not found

        Raises:
            VaultError: If secret deletion fails (other than not found)
        """
        try:
            key = self._parse_reference(reference)

            # Delete metadata (this deletes all versions in KV v2)
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=self._normalize_key(key),
                mount_point=self.vault_mount,
            )

            logger.debug("Deleted secret: %s", reference)
            return True

        except InvalidPath:
            logger.warning("Secret not found for deletion: %s", reference)
            return False
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to delete secret: %s", e)
            raise VaultError(f"Failed to delete secret: {e}") from e

    def update_secret(
        self, reference: str, value: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Update an existing secret in Vault.

        Args:
            reference: The reference to the secret
            value: New secret value
            metadata: Optional new metadata

        Returns:
            True if updated, False if not found

        Raises:
            VaultError: If secret update fails (other than not found)
        """
        try:
            key = self._parse_reference(reference)

            # Check if secret exists first
            try:
                self.client.secrets.kv.v2.read_secret_version(
                    path=self._normalize_key(key),
                    mount_point=self.vault_mount,
                )
            except InvalidPath:
                logger.warning("Secret not found for update: %s", reference)
                return False

            # Update the secret (creates a new version in KV v2)
            secret_data = {"value": value}
            if metadata:
                secret_data["metadata"] = metadata

            self.client.secrets.kv.v2.create_or_update_secret(
                path=self._normalize_key(key),
                secret=secret_data,
                mount_point=self.vault_mount,
            )

            logger.debug("Updated secret: %s", reference)
            return True

        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to update secret: %s", e)
            raise VaultError(f"Failed to update secret: {e}") from e

    def list_secrets(self, prefix: str | None = None, max_depth: int = 10) -> list[str]:
        """List all secret references in Vault.

        Args:
            prefix: Optional prefix to filter secrets
            max_depth: Maximum directory depth to traverse (default: 10)

        Returns:
            List of secret references

        Raises:
            VaultError: If listing fails
        """
        try:
            # Use iterative approach with a queue to avoid deep recursion
            refs = []
            queue = [(self._normalize_key(prefix) if prefix else "", 0)]  # (path, depth)

            while queue:
                current_path, depth = queue.pop(0)

                # Check depth limit
                if depth >= max_depth:
                    logger.warning(
                        "Maximum depth (%d) reached for path: %s", max_depth, current_path
                    )
                    continue

                try:
                    response = self.client.secrets.kv.v2.list_secrets(
                        path=current_path,
                        mount_point=self.vault_mount,
                    )
                    keys = response["data"]["keys"]
                except InvalidPath:
                    # No secrets at this path
                    continue

                # Process keys
                for key in keys:
                    if key.endswith("/"):
                        # This is a directory, add to queue for processing
                        stripped_key = key.rstrip("/")
                        subpath = (
                            f"{current_path}/{stripped_key}" if current_path else stripped_key
                        )
                        queue.append((subpath, depth + 1))
                    else:
                        # This is a secret, add reference
                        full_key = f"{current_path}/{key}" if current_path else key
                        refs.append(f"vault://{full_key}")

            return refs

        except Exception as e:
            logger.error("Failed to list secrets: %s", e)
            raise VaultError(f"Failed to list secrets: {e}") from e
