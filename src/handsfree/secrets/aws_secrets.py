"""AWS Secrets Manager-based secret manager.

This implementation provides production-ready secret storage using AWS Secrets Manager.
It uses standard boto3 credential resolution (environment variables, IAM roles, IRSA, etc.).
"""

import json
import logging
import os
from typing import Any

from .interface import SecretManager

logger = logging.getLogger(__name__)


class AWSSecretManager(SecretManager):
    """Secret manager that stores secrets in AWS Secrets Manager.

    This implementation is suitable for:
    - Production environments in AWS
    - Multi-tenant deployments
    - Environments requiring audit logs for secret access
    - Environments using AWS IAM for authentication

    Configuration:
    - AWS_REGION or AWS_DEFAULT_REGION: AWS region (required)
    - HANDSFREE_AWS_SECRETS_PREFIX: Optional prefix for secret names (default: "handsfree/")
    - AWS credentials via standard boto3 resolution (env vars, IAM role, IRSA, etc.)

    Security features:
    - Encryption at rest (handled by AWS Secrets Manager)
    - Access audit logging via AWS CloudTrail
    - IAM-based authentication and authorization
    - Automatic secret versioning
    """

    def __init__(
        self,
        region: str | None = None,
        prefix: str | None = None,
        boto3_client: Any | None = None,
    ):
        """Initialize the AWS Secrets Manager secret manager.

        Args:
            region: AWS region (default: from AWS_REGION or AWS_DEFAULT_REGION env var)
            prefix: Prefix for secret names (default: from HANDSFREE_AWS_SECRETS_PREFIX
                or "handsfree/")
            boto3_client: Optional boto3 client for testing (default: creates new client)

        Raises:
            ImportError: If boto3 is not installed
            ValueError: If AWS region is not configured
        """
        # Import boto3 only when needed (optional dependency)
        try:
            import boto3
            from botocore.exceptions import ClientError, NoRegionError

            self._boto3 = boto3
            self._ClientError = ClientError
            self._NoRegionError = NoRegionError
        except ImportError as e:
            raise ImportError(
                "boto3 is required for AWS Secrets Manager support. "
                "Install it with: pip install boto3"
            ) from e

        # Load configuration
        self.region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        self.prefix = prefix or os.getenv("HANDSFREE_AWS_SECRETS_PREFIX", "handsfree/")

        # Validate configuration
        if not self.region:
            raise ValueError(
                "AWS region is required. Set AWS_REGION or AWS_DEFAULT_REGION environment variable."
            )

        # Ensure prefix ends with /
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix = f"{self.prefix}/"

        # Initialize AWS Secrets Manager client
        if boto3_client is not None:
            self.client = boto3_client
        else:
            try:
                self.client = self._boto3.client("secretsmanager", region_name=self.region)
            except self._NoRegionError as e:
                raise ValueError(f"Failed to initialize AWS client: {e}") from e

        logger.info(
            "Initialized AWSSecretManager with region: %s, prefix: %s", self.region, self.prefix
        )

    def _make_secret_name(self, key: str) -> str:
        """Convert a secret key to an AWS Secrets Manager secret name.

        Args:
            key: Secret key (e.g., "github_token_user_123")

        Returns:
            Secret name with prefix (e.g., "handsfree/github_token_user_123")
        """
        return f"{self.prefix}{key}"

    def _parse_reference(self, reference: str) -> str:
        """Parse a reference to get the secret name.

        Args:
            reference: Reference string (format: "aws://secret_name")

        Returns:
            Secret name

        Raises:
            ValueError: If reference format is invalid
        """
        if not reference.startswith("aws://"):
            raise ValueError(f"Invalid reference format: {reference}")
        return reference[6:]  # Strip "aws://" prefix

    def store_secret(self, key: str, value: str, metadata: dict[str, str] | None = None) -> str:
        """Store a secret in AWS Secrets Manager.

        Args:
            key: Unique identifier for the secret
            value: The secret value
            metadata: Optional metadata to store with the secret (stored as tags)

        Returns:
            Reference string (format: "aws://secret_name")

        Raises:
            Exception: If secret storage fails
        """
        try:
            secret_name = self._make_secret_name(key)

            # Prepare secret string (AWS Secrets Manager stores JSON or plain text)
            secret_string = json.dumps({"value": value})

            # Prepare tags if metadata provided
            tags = []
            if metadata:
                # Convert metadata dict to AWS tags format
                tags = [{"Key": k, "Value": v} for k, v in metadata.items()]

            # Try to create the secret
            try:
                create_params = {
                    "Name": secret_name,
                    "SecretString": secret_string,
                }
                if tags:
                    create_params["Tags"] = tags

                self.client.create_secret(**create_params)
                logger.debug("Created secret with key: %s", key)
            except self._ClientError as e:
                # If secret already exists, update it instead
                if e.response["Error"]["Code"] == "ResourceExistsException":
                    self.client.put_secret_value(
                        SecretId=secret_name,
                        SecretString=secret_string,
                    )
                    # Update tags if provided
                    if tags:
                        self.client.tag_resource(SecretId=secret_name, Tags=tags)
                    logger.debug("Updated existing secret with key: %s", key)
                else:
                    raise

            return f"aws://{secret_name}"

        except Exception as e:
            logger.error("Failed to store secret: %s", e)
            raise Exception(f"Failed to store secret: {e}") from e

    def get_secret(self, reference: str) -> str | None:
        """Retrieve a secret from AWS Secrets Manager.

        Args:
            reference: The reference string

        Returns:
            The secret value, or None if not found

        Raises:
            Exception: If secret retrieval fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)

            # Get secret value
            response = self.client.get_secret_value(SecretId=secret_name)

            # Parse the secret string
            secret_data = json.loads(response["SecretString"])
            return secret_data.get("value")

        except self._ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("ResourceNotFoundException", "InvalidRequestException"):
                logger.warning("Secret not found: %s", reference)
                return None
            logger.error("Failed to retrieve secret: %s", e)
            raise Exception(f"Failed to retrieve secret: {e}") from e
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to retrieve secret: %s", e)
            raise Exception(f"Failed to retrieve secret: {e}") from e

    def delete_secret(self, reference: str) -> bool:
        """Delete a secret from AWS Secrets Manager.

        Note: AWS Secrets Manager schedules secrets for deletion with a recovery window.
        This uses ForceDeleteWithoutRecovery=True for immediate deletion in tests/dev.
        For production, consider using a recovery window.

        Args:
            reference: The reference to the secret

        Returns:
            True if deleted, False if not found

        Raises:
            Exception: If secret deletion fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)

            # Delete the secret (with immediate deletion, no recovery window)
            self.client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True,
            )

            logger.debug("Deleted secret: %s", reference)
            return True

        except self._ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("ResourceNotFoundException", "InvalidRequestException"):
                logger.warning("Secret not found for deletion: %s", reference)
                return False
            logger.error("Failed to delete secret: %s", e)
            raise Exception(f"Failed to delete secret: {e}") from e
        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to delete secret: %s", e)
            raise Exception(f"Failed to delete secret: {e}") from e

    def update_secret(
        self, reference: str, value: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Update an existing secret in AWS Secrets Manager.

        Args:
            reference: The reference to the secret
            value: New secret value
            metadata: Optional new metadata (updates tags)

        Returns:
            True if updated, False if not found

        Raises:
            Exception: If secret update fails (other than not found)
        """
        try:
            secret_name = self._parse_reference(reference)

            # Check if secret exists by attempting to describe it
            try:
                self.client.describe_secret(SecretId=secret_name)
            except self._ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ("ResourceNotFoundException", "InvalidRequestException"):
                    logger.warning("Secret not found for update: %s", reference)
                    return False
                raise

            # Update the secret value
            secret_string = json.dumps({"value": value})
            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_string,
            )

            # Update tags if metadata provided
            if metadata:
                tags = [{"Key": k, "Value": v} for k, v in metadata.items()]
                self.client.tag_resource(SecretId=secret_name, Tags=tags)

            logger.debug("Updated secret: %s", reference)
            return True

        except ValueError as e:
            logger.error("Invalid reference format: %s", e)
            return False
        except Exception as e:
            logger.error("Failed to update secret: %s", e)
            raise Exception(f"Failed to update secret: {e}") from e

    def list_secrets(self, prefix: str | None = None) -> list[str]:
        """List all secret references in AWS Secrets Manager.

        Args:
            prefix: Optional prefix to filter secrets (appended to the manager's prefix)

        Returns:
            List of secret references

        Raises:
            Exception: If listing fails
        """
        try:
            refs = []
            
            # Determine the full prefix to search for
            search_prefix = self.prefix
            if prefix:
                search_prefix = self._make_secret_name(prefix)

            # Use paginator to handle large numbers of secrets
            paginator = self.client.get_paginator("list_secrets")
            
            # List secrets with optional filter
            page_params = {}
            if search_prefix:
                # AWS Secrets Manager doesn't have a direct prefix filter,
                # so we'll filter in memory after retrieving
                page_params["Filters"] = [
                    {
                        "Key": "name",
                        "Values": [search_prefix],
                    }
                ]

            for page in paginator.paginate(**page_params):
                for secret in page.get("SecretList", []):
                    secret_name = secret["Name"]
                    
                    # Filter by prefix if specified
                    if search_prefix and not secret_name.startswith(search_prefix):
                        continue
                    
                    # Skip secrets scheduled for deletion
                    if "DeletedDate" in secret:
                        continue
                    
                    refs.append(f"aws://{secret_name}")

            return refs

        except Exception as e:
            logger.error("Failed to list secrets: %s", e)
            raise Exception(f"Failed to list secrets: {e}") from e
