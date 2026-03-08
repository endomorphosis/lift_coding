"""Shared AI capability registry for CLI and ipfs_datasets_py backends."""

from .capabilities import (
    execute_ai_capability,
    execute_ai_request,
    get_ai_capability,
    list_ai_capabilities,
)
from .models import (
    AICapabilityRequest,
    AICapabilityResult,
    AICapabilitySpec,
    AIBackendFamily,
    AIExecutionMode,
    AIRequestContext,
)

__all__ = [
    "AICapabilityRequest",
    "AICapabilityResult",
    "AICapabilitySpec",
    "AIBackendFamily",
    "AIExecutionMode",
    "AIRequestContext",
    "execute_ai_capability",
    "execute_ai_request",
    "get_ai_capability",
    "list_ai_capabilities",
]
