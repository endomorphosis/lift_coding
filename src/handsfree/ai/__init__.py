"""Shared AI capability registry for CLI and ipfs_datasets_py backends."""

from .capabilities import (
    execute_ai_capability,
    execute_ai_request,
    get_ai_capability,
    list_ai_capabilities,
)
from .history import discover_failure_history_cids
from .observability import build_ai_backend_policy_report
from .models import (
    AICapabilityRequest,
    AICapabilityResult,
    AICapabilitySpec,
    AIBackendFamily,
    AIExecutionMode,
    AIRequestContext,
)
from .policy import (
    AIBackendPolicy,
    build_policy_resolution,
    get_ai_backend_policy,
    resolve_policy_workflow,
)
from .serialization import build_api_execute_response

__all__ = [
    "AICapabilityRequest",
    "AICapabilityResult",
    "AICapabilitySpec",
    "AIBackendFamily",
    "AIBackendPolicy",
    "AIExecutionMode",
    "AIRequestContext",
    "build_ai_backend_policy_report",
    "build_policy_resolution",
    "build_api_execute_response",
    "discover_failure_history_cids",
    "execute_ai_capability",
    "execute_ai_request",
    "get_ai_backend_policy",
    "get_ai_capability",
    "list_ai_capabilities",
    "resolve_policy_workflow",
]
