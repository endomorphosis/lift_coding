"""Environment variable-based secret manager.

This is a simple implementation for development/testing that stores secrets
as environment variables. NOT recommended for production use.
"""

import logging
import os

from .interface import SecretManager

logger = logging.getLogger(__name__)


class EnvSecretManager(SecretManager):
    """Secret manager that stores secrets as environment variables.

    This implementation is suitable for:
    - Local development
    - Testing
    - Simple deployments where env vars are acceptable

    NOT suitable for:
    - Production environments requiring rotation
    - Multi-tenant deployments
    - Environments requiring audit logs for secret access

    Security note:
    - Secrets are stored in process memory (environment variables)
    - No encryption at rest
    - No access audit logging
    - Use AWS Secrets Manager, Vault, or similar for production
    """

    def __init__(self, prefix: str = "HANDSFREE_SECRET_"):
        """Initialize the environment secret manager.

        Args:
            prefix: Prefix for environment variable names (default: "HANDSFREE_SECRET_")
        """
        self.prefix = prefix
        logger.info("Initialized EnvSecretManager with prefix: %s", prefix)

    def _make_env_key(self, key: str) -> str:
        """Convert a secret key to an environment variable name.

        Args:
            key: Secret key (e.g., "github_token_user_123")

        Returns:
            Environment variable name (e.g., "HANDSFREE_SECRET_GITHUB_TOKEN_USER_123")
        """
        # Convert to uppercase and replace special chars with underscores
        env_key = key.upper().replace("-", "_").replace(".", "_").replace("/", "_")
        return f"{self.prefix}{env_key}"

    def _parse_reference(self, reference: str) -> str:
        """Parse a reference to get the environment variable name.

        Args:
            reference: Reference string (format: "env://HANDSFREE_SECRET_GITHUB_TOKEN_USER_123")

        Returns:
            Environment variable name
        """
        if not reference.startswith("env://"):
            raise ValueError(f"Invalid reference format: {reference}")
        return reference[6:]  # Strip "env://" prefix

    def store_secret(self, key: str, value: str, metadata: dict[str, str] | None = None) -> str:
        """Store a secret as an environment variable.

        Args:
            key: Unique identifier for the secret
            value: The secret value
            metadata: Ignored in this implementation

        Returns:
            Reference string (format: "env://VAR_NAME")
        """
        env_key = self._make_env_key(key)
        os.environ[env_key] = value
        logger.debug("Stored secret with key: %s", key)
        return f"env://{env_key}"

    def get_secret(self, reference: str) -> str | None:
        """Retrieve a secret from environment variables.

        Args:
            reference: The reference string

        Returns:
            The secret value, or None if not found
        """
        try:
            env_key = self._parse_reference(reference)
            value = os.environ.get(env_key)
            if value is None:
                logger.warning("Secret not found: %s", reference)
            return value
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return None

    def delete_secret(self, reference: str) -> bool:
        """Delete a secret from environment variables.

        Args:
            reference: The reference to the secret

        Returns:
            True if deleted, False if not found
        """
        try:
            env_key = self._parse_reference(reference)
            if env_key in os.environ:
                del os.environ[env_key]
                logger.debug("Deleted secret: %s", reference)
                return True
            logger.warning("Secret not found for deletion: %s", reference)
            return False
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False

    def update_secret(
        self, reference: str, value: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Update an existing secret.

        Args:
            reference: The reference to the secret
            value: New secret value
            metadata: Ignored in this implementation

        Returns:
            True if updated, False if not found
        """
        try:
            env_key = self._parse_reference(reference)
            if env_key in os.environ:
                os.environ[env_key] = value
                logger.debug("Updated secret: %s", reference)
                return True
            logger.warning("Secret not found for update: %s", reference)
            return False
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False

    def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List all secret references.

        Args:
            prefix: Optional prefix to filter secrets

        Returns:
            List of secret references
        """
        refs = []
        search_prefix = self.prefix if prefix is None else self._make_env_key(prefix)

        for env_key in os.environ:
            if env_key.startswith(search_prefix):
                refs.append(f"env://{env_key}")

        return refs
