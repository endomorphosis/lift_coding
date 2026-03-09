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
    preferred_execution_mode: str | None = None
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


@dataclass(frozen=True)
class MCPArtifactRefs:
    """Normalized artifact and provenance references for one execution."""

    result_cid: str | None = None
    receipt_ref: str | None = None
    event_dag_ref: str | None = None
    delegation_ref: str | None = None


@dataclass(frozen=True)
class MCPExecutionTrace:
    """Normalized execution trace metadata."""

    request_id: str | None = None
    run_id: str | None = None
    remote_task_id: str | None = None
    tool_name: str | None = None
    last_protocol_state: str | None = None
    provider_profiles: tuple[str, ...] = ()


@dataclass(frozen=True)
class MCPExecutionResultEnvelope:
    """Canonical HandsFree result envelope for direct or MCP-backed execution."""

    capability_id: str | None
    provider: str
    server_family: str
    execution_mode: str
    status: str
    spoken_text: str
    summary: str
    structured_output: Any = None
    follow_up_actions: list[dict[str, Any]] = field(default_factory=list)
    artifact_refs: MCPArtifactRefs = field(default_factory=MCPArtifactRefs)
    trace: MCPExecutionTrace = field(default_factory=MCPExecutionTrace)
    needs_input_schema: dict[str, Any] | None = None
