"""Typed models for the MCP++ scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single MCP server family."""

    server_family: str
    endpoint: str
    auth_secret: str | None = None
    timeout_s: float = 30.0
    poll_interval_s: float = 2.0
    enabled: bool = True
    tool_name: str | None = None
    rpc_path: str = "/mcp"
    protocol_version: str = "2024-11-05"
    client_name: str = "handsfree-dev-companion"
    client_version: str = "0.0.0"
    transport: str = "http"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    task_category: str | None = None
    task_create_tool: str | None = None
    task_status_tool: str | None = None
    task_cancel_tool: str | None = None


@dataclass(frozen=True)
class MCPToolInvocationResult:
    """Normalized result from an MCP tool invocation."""

    request_id: str | None
    run_id: str | None
    status: str
    tool_name: str
    output: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
    content: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class MCPRunStatus:
    """Normalized status for an MCP run."""

    run_id: str
    status: str
    message: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
