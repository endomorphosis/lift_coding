"""Google Cloud Secret Manager-based secret manager.

This implementation provides production-ready secret storage using Google Cloud Secret Manager.
It uses Application Default Credentials (ADC) for authentication.
"""

import logging
import os
import re

from google.api_core.exceptions import AlreadyExists, NotFound, GoogleAPIError
from google.cloud import secretmanager

from .interface import SecretManager

logger = logging.getLogger(__name__)


class GCPSecretManager(SecretManager):
    """Secret manager that stores secrets in Google Cloud Secret Manager.

    This implementation is suitable for:
    - Production environments on Google Cloud Platform
    - Multi-tenant deployments
    - Environments requiring audit logs for secret access
    - Secrets rotation workflows

    Configuration:
    - GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID: GCP project ID (required)
    - HANDSFREE_GCP_SECRETS_PREFIX: Optional prefix for secret names (default: "handsfree")
    - Authentication via Google Application Default Credentials (ADC):
      - Service account key file via GOOGLE_APPLICATION_CREDENTIALS
      - Workload Identity (for GKE)
      - gcloud auth application-default login (for development)

    Security features:
    - Encryption at rest (handled by GCP Secret Manager)
    - Access audit logging (via Cloud Audit Logs)
    - IAM-based access control
    - Automatic secret versioning
    - TLS/HTTPS communication
    """

    def __init__(
        self,
        project_id: str | None = None,
        prefix: str | None = None,
    ):
        """Initialize the GCP Secret Manager.

        Args:
            project_id: GCP project ID (default: from GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID env var)
            prefix: Prefix for secret names (default: from HANDSFREE_GCP_SECRETS_PREFIX env var or "handsfree")

        Raises:
            ValueError: If required configuration is missing
            GoogleAPIError: If connection to Secret Manager fails
        """
        # Load configuration from environment variables or parameters
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        self.prefix = prefix or os.getenv("HANDSFREE_GCP_SECRETS_PREFIX", "handsfree")

        # Validate configuration
        self._validate_config()

        # Initialize Secret Manager client
        try:
            self.client = secretmanager.SecretManagerServiceClient()
            logger.info(
                "Initialized GCPSecretManager with project: %s, prefix: %s",
                self.project_id,
                self.prefix,
            )
        except Exception as e:
            logger.error("Failed to initialize Secret Manager client: %s", e)
            raise GoogleAPIError(f"Failed to initialize Secret Manager client: {e}") from e

    def _validate_config(self) -> None:
        """Validate the GCP Secret Manager configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID environment variable or project_id parameter is required"
            )

    def _make_secret_name(self, key: str) -> str:
        """Convert a secret key to a GCP secret name.

        Args:
            key: Secret key (e.g., "github_token_user_123")

        Returns:
            Secret name with prefix (e.g., "handsfree-github-token-user-123")
        """
        # GCP secret names must match ^[a-zA-Z0-9_-]+$
        # For consistency, convert underscores to hyphens and replace other invalid characters
        normalized = re.sub(r'[^a-zA-Z0-9-]', '-', key).lower()
        # Remove consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)
        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')
        return f"{self.prefix}-{normalized}"

    def _get_secret_path(self, secret_name: str) -> str:
        """Get the full resource path for a secret.

        Args:
            secret_name: Secret name (without project prefix)

        Returns:
            Full resource path (e.g., "projects/my-project/secrets/handsfree-github-token-user-123")
        """
        return f"projects/{self.project_id}/secrets/{secret_name}"

    def _get_secret_version_path(self, secret_name: str, version: str = "latest") -> str:
        """Get the full resource path for a secret version.

        Args:
            secret_name: Secret name (without project prefix)
            version: Version identifier (default: "latest")

        Returns:
            Full version path (e.g., "projects/my-project/secrets/my-secret/versions/latest")
        """
        return f"{self._get_secret_path(secret_name)}/versions/{version}"

    def _parse_reference(self, reference: str) -> str:
        """Parse a reference to get the secret name.

        Args:
            reference: Reference string (format: "gcp://secret_name")

        Returns:
            Secret name

        Raises:
            ValueError: If reference format is invalid
        """
        if not reference.startswith("gcp://"):
            raise ValueError(f"Invalid reference format: {reference}")
        return reference[6:]  # Strip "gcp://" prefix

    def _normalize_metadata_to_labels(self, metadata: dict[str, str] | None) -> dict[str, str]:
        """Normalize metadata to GCP-compliant labels.

        GCP labels have restrictions: lowercase, alphanumeric, hyphens.
        Label keys and values are truncated to 63 characters.
        Label keys must start with a lowercase letter.

        Args:
            metadata: Optional metadata dictionary

        Returns:
            Dictionary of normalized labels
        """
        labels = {}
        if metadata:
            for k, v in metadata.items():
                label_key = self._normalize_label_string(k)[:63]
                label_value = self._normalize_label_string(v)[:63]
                # Ensure key starts with a lowercase letter
                if label_key and not label_key[0].islower():
                    label_key = f"x-{label_key}"[:63]
                if label_key:  # Only add if key is non-empty after normalization
                    labels[label_key] = label_value
        return labels

    def _normalize_label_string(self, text: str) -> str:
        """Normalize a string to GCP label format.

        GCP labels can only contain lowercase letters, numbers, underscores, and hyphens.
        For consistency, convert underscores to hyphens.

        Args:
            text: String to normalize

        Returns:
            Normalized string (lowercase, invalid characters replaced with hyphens)
        """
        # Convert to lowercase and replace invalid characters (including underscores) with hyphens
        normalized = re.sub(r'[^a-z0-9-]', '-', text.lower())
        # Remove consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)
        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')
        return normalized

    def store_secret(self, key: str, value: str, metadata: dict[str, str] | None = None) -> str:
        """Store a secret in Google Cloud Secret Manager.

        Args:
            key: Unique identifier for the secret
            value: The secret value
            metadata: Optional metadata to store with the secret (stored as labels)

        Returns:
            Reference string (format: "gcp://secret_name")

        Raises:
            GoogleAPIError: If secret storage fails
        """
        try:
            secret_name = self._make_secret_name(key)
            parent = f"projects/{self.project_id}"

            # Prepare labels from metadata
            labels = self._normalize_metadata_to_labels(metadata)

            # Create the secret
            try:
                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_name,
                        "secret": {
                            "replication": {"automatic": {}},
                            "labels": labels,
                        },
                    }
                )
                logger.debug("Created secret: %s", secret_name)
            except AlreadyExists:
                # Secret already exists, update labels if metadata provided
                logger.debug("Secret already exists: %s", secret_name)
                if metadata:
                    secret_path = self._get_secret_path(secret_name)
                    self.client.update_secret(
                        request={
                            "secret": {
                                "name": secret_path,
                                "labels": labels,
                            },
                            "update_mask": {"paths": ["labels"]},
                        }
                    )
                    logger.debug("Updated labels for existing secret: %s", secret_name)

            # Add the secret version with the actual value
            secret_path = self._get_secret_path(secret_name)
            self.client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": value.encode("utf-8")},
                }
            )

            logger.debug("Stored secret with key: %s", key)
            return f"gcp://{secret_name}"

        except (AlreadyExists, NotFound, ValueError):
            # These are already handled above
            raise
        except GoogleAPIError:
            # Don't wrap GoogleAPIError in another GoogleAPIError
            raise
        except Exception as e:
            logger.error("Failed to store secret: %s", e)
            raise GoogleAPIError(f"Failed to store secret: {e}") from e

    def get_secret(self, reference: str) -> str | None:
        """Retrieve a secret from Google Cloud Secret Manager.

        Args:
            reference: The reference string

        Returns:
            The secret value, or None if not found

        Raises:
            GoogleAPIError: If secret retrieval fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)
            version_path = self._get_secret_version_path(secret_name, "latest")

            # Access the secret version
            response = self.client.access_secret_version(request={"name": version_path})

            # Return the decoded payload
            return response.payload.data.decode("utf-8")

        except NotFound:
            logger.warning("Secret not found: %s", reference)
            return None
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return None
        except GoogleAPIError:
            # Don't wrap GoogleAPIError in another GoogleAPIError
            raise
        except Exception as e:
            logger.error("Failed to retrieve secret: %s", e)
            raise GoogleAPIError(f"Failed to retrieve secret: {e}") from e

    def delete_secret(self, reference: str) -> bool:
        """Delete a secret from Google Cloud Secret Manager.

        Args:
            reference: The reference to the secret

        Returns:
            True if deleted, False if not found

        Raises:
            GoogleAPIError: If secret deletion fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)
            secret_path = self._get_secret_path(secret_name)

            # Delete the secret (deletes all versions)
            self.client.delete_secret(request={"name": secret_path})

            logger.debug("Deleted secret: %s", reference)
            return True

        except NotFound:
            logger.warning("Secret not found for deletion: %s", reference)
            return False
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except GoogleAPIError:
            # Don't wrap GoogleAPIError in another GoogleAPIError
            raise
        except Exception as e:
            logger.error("Failed to delete secret: %s", e)
            raise GoogleAPIError(f"Failed to delete secret: {e}") from e

    def update_secret(
        self, reference: str, value: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Update an existing secret in Google Cloud Secret Manager.

        This creates a new version of the secret with the updated value.

        Args:
            reference: The reference to the secret
            value: New secret value
            metadata: Optional new metadata (updates labels on the secret)

        Returns:
            True if updated, False if not found

        Raises:
            GoogleAPIError: If secret update fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)
            secret_path = self._get_secret_path(secret_name)

            # Check if secret exists by trying to get it
            try:
                self.client.get_secret(request={"name": secret_path})
            except NotFound:
                logger.warning("Secret not found for update: %s", reference)
                return False

            # Update labels if metadata provided
            if metadata:
                labels = self._normalize_metadata_to_labels(metadata)

                self.client.update_secret(
                    request={
                        "secret": {
                            "name": secret_path,
                            "labels": labels,
                        },
                        "update_mask": {"paths": ["labels"]},
                    }
                )

            # Add new version with updated value
            self.client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": value.encode("utf-8")},
                }
            )

            logger.debug("Updated secret: %s", reference)
            return True

        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except NotFound:
            # This is handled in the method body
            raise
        except GoogleAPIError:
            # Don't wrap GoogleAPIError in another GoogleAPIError
            raise
        except Exception as e:
            logger.error("Failed to update secret: %s", e)
            raise GoogleAPIError(f"Failed to update secret: {e}") from e

    def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List all secret references in Google Cloud Secret Manager.

        Args:
            prefix: Optional prefix to filter secrets (applied after the manager's prefix)

        Returns:
            List of secret references

        Raises:
            GoogleAPIError: If listing fails
        """
        try:
            parent = f"projects/{self.project_id}"
            refs = []

            # List all secrets in the project
            for secret in self.client.list_secrets(request={"parent": parent}):
                # Extract secret name from full path (projects/{project}/secrets/{name})
                secret_name = secret.name.split("/")[-1]

                # Check if secret matches our prefix
                if not secret_name.startswith(f"{self.prefix}-"):
                    continue

                # Apply additional prefix filter if provided
                if prefix:
                    full_prefix = self._make_secret_name(prefix)
                    if not secret_name.startswith(full_prefix):
                        continue

                refs.append(f"gcp://{secret_name}")

            return refs

        except GoogleAPIError:
            # Don't wrap GoogleAPIError in another GoogleAPIError
            raise
        except Exception as e:
            logger.error("Failed to list secrets: %s", e)
            raise GoogleAPIError(f"Failed to list secrets: {e}") from e
