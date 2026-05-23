"""Shared AI capability registry for CLI and ipfs_datasets_py backends."""

from .capabilities import (
    execute_ai_capability,
    execute_ai_request,
    get_ai_capability,
    list_ai_capabilities,
)
from .capability_registry import (
    build_virtual_ai_os_execution_matrix,
    get_virtual_ai_os_capability,
    list_virtual_ai_os_capabilities,
    resolve_virtual_ai_os_execution_mode,
)
from .runtime_router import resolve_virtual_ai_os_runtime_route
from .history import discover_failure_history_cids
from .observability import (
    build_ai_backend_policy_config,
    build_ai_backend_policy_history_report,
    build_ai_backend_policy_report,
    build_latest_snapshot_info,
    build_snapshot_policy_config,
    build_snapshot_health,
    build_snapshot_summary,
)
from .models import (
    AICapabilityRequest,
    AICapabilityRegistryEntry,
    AICapabilityRoute,
    AICapabilityResult,
    AICapabilitySpec,
    AIBackendFamily,
    AIExecutionMode,
    AIRequestContext,
    CapabilityConfirmationPolicy,
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
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
    "AICapabilityRegistryEntry",
    "AICapabilityRoute",
    "AICapabilityResult",
    "AICapabilitySpec",
    "AIBackendFamily",
    "AIBackendPolicy",
    "AIExecutionMode",
    "AIRequestContext",
    "CapabilityConfirmationPolicy",
    "CapabilityExecutionMode",
    "CapabilityRuntimeSurface",
    "build_ai_backend_policy_config",
    "build_ai_backend_policy_history_report",
    "build_ai_backend_policy_report",
    "build_latest_snapshot_info",
    "build_snapshot_policy_config",
    "build_snapshot_health",
    "build_snapshot_summary",
    "build_virtual_ai_os_execution_matrix",
    "build_policy_resolution",
    "build_api_execute_response",
    "discover_failure_history_cids",
    "execute_ai_capability",
    "execute_ai_request",
    "get_ai_backend_policy",
    "get_ai_capability",
    "get_virtual_ai_os_capability",
    "list_ai_capabilities",
    "list_virtual_ai_os_capabilities",
    "resolve_policy_workflow",
    "resolve_virtual_ai_os_execution_mode",
    "resolve_virtual_ai_os_runtime_route",
]
