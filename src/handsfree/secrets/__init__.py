"""Secret management interfaces and implementations.

This module provides production-ready abstractions for storing and retrieving
secrets (like GitHub tokens) from various secret management backends.
"""

from .env_secrets import EnvSecretManager
from .factory import get_secret_manager
from .interface import SecretManager

__all__ = [
    "SecretManager",
    "EnvSecretManager",
    "get_secret_manager",
]
