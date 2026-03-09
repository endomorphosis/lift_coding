"""MCP++ integration helpers for HandsFree."""

from .capabilities import (
    MCPTaskBinding,
    MCPToolCall,
    build_result_envelope,
    build_result_envelope_from_invocation,
    envelope_to_trace,
    resolve_task_binding,
)
from .catalog import (
    MCPCapabilityDescriptor,
    MCPProviderDescriptor,
    get_capability_descriptor,
    get_provider_capabilities,
    get_provider_descriptor,
    infer_provider_capability,
    provider_supports_capability,
    resolve_capability_execution_mode,
    resolve_provider_alias,
    resolve_provider_capability,
    resolve_provider_name_for_server_family,
)
from .client import MCPClient, MCPClientError, MCPConfigurationError
from .config import get_mcp_server_config, is_mcp_provider_enabled
from .models import (
    MCPArtifactRefs,
    MCPExecutionResultEnvelope,
    MCPExecutionTrace,
    MCPRunStatus,
    MCPServerConfig,
    MCPToolInvocationResult,
)

__all__ = [
    "MCPTaskBinding",
    "MCPClient",
    "MCPClientError",
    "MCPArtifactRefs",
    "MCPCapabilityDescriptor",
    "MCPConfigurationError",
    "MCPExecutionResultEnvelope",
    "MCPExecutionTrace",
    "MCPProviderDescriptor",
    "MCPRunStatus",
    "MCPServerConfig",
    "MCPToolInvocationResult",
    "MCPToolCall",
    "build_result_envelope",
    "build_result_envelope_from_invocation",
    "envelope_to_trace",
    "get_capability_descriptor",
    "get_mcp_server_config",
    "get_provider_capabilities",
    "get_provider_descriptor",
    "infer_provider_capability",
    "is_mcp_provider_enabled",
    "provider_supports_capability",
    "resolve_capability_execution_mode",
    "resolve_provider_alias",
    "resolve_provider_capability",
    "resolve_provider_name_for_server_family",
    "resolve_task_binding",
]
