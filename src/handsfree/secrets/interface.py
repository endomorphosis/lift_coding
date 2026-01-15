"""Secret Manager interface definition.

This module defines the abstract interface that all secret storage backends must implement.
"""

from abc import ABC, abstractmethod


class SecretManager(ABC):
    """Abstract interface for secret storage backends.

    All secret managers must implement this interface to provide a consistent
    API for storing and retrieving secrets across different backends (env vars,
    AWS Secrets Manager, HashiCorp Vault, Google Secret Manager, etc.).

    Security considerations:
    - Secrets are never logged or persisted to application database
    - Only references (token_ref) are stored in the database
    - Actual secret values are retrieved on-demand from the secret manager
    - Secret managers should handle encryption at rest
    """

    @abstractmethod
    def store_secret(self, key: str, value: str, metadata: dict[str, str] | None = None) -> str:
        """Store a secret and return a reference to it.

        Args:
            key: Unique identifier for the secret (e.g., "github_token_user_123")
            value: The actual secret value (e.g., GitHub token)
            metadata: Optional metadata to store with the secret (e.g., scopes, expiry)

        Returns:
            Reference string that can be used to retrieve the secret later
            (this is what gets stored as token_ref in the database)

        Raises:
            Exception: If secret storage fails
        """
        pass

    @abstractmethod
    def get_secret(self, reference: str) -> str | None:
        """Retrieve a secret using its reference.

        Args:
            reference: The reference returned by store_secret()

        Returns:
            The secret value, or None if not found

        Raises:
            Exception: If secret retrieval fails
        """
        pass

    @abstractmethod
    def delete_secret(self, reference: str) -> bool:
        """Delete a secret using its reference.

        Args:
            reference: The reference to the secret

        Returns:
            True if deleted, False if not found

        Raises:
            Exception: If secret deletion fails
        """
        pass

    @abstractmethod
    def update_secret(
        self, reference: str, value: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Update an existing secret.

        Args:
            reference: The reference to the secret
            value: New secret value
            metadata: Optional new metadata

        Returns:
            True if updated, False if not found

        Raises:
            Exception: If secret update fails
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List all secret references, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter secrets (e.g., "github_token_")

        Returns:
            List of secret references

        Raises:
            Exception: If listing fails
        """
        pass
