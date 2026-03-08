"""MCP++ integration helpers for HandsFree."""

from .capabilities import MCPTaskBinding, MCPToolCall, resolve_task_binding
from .catalog import get_provider_descriptor, infer_provider_capability, resolve_provider_alias
from .client import MCPClient, MCPClientError, MCPConfigurationError
from .config import get_mcp_server_config, is_mcp_provider_enabled
from .models import MCPRunStatus, MCPServerConfig, MCPToolInvocationResult

__all__ = [
    "MCPTaskBinding",
    "MCPClient",
    "MCPClientError",
    "MCPConfigurationError",
    "MCPRunStatus",
    "MCPServerConfig",
    "MCPToolInvocationResult",
    "MCPToolCall",
    "get_mcp_server_config",
    "get_provider_descriptor",
    "infer_provider_capability",
    "is_mcp_provider_enabled",
    "resolve_provider_alias",
    "resolve_task_binding",
]
