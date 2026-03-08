"""Typed models for shared AI capability routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AIBackendFamily(str, Enum):
    """Normalized backend families for AI capabilities."""

    COPILOT_CLI = "copilot_cli"
    GITHUB_CLI = "github_cli"
    IPFS_LLM_ROUTER = "ipfs_llm_router"
    IPFS_EMBEDDINGS_ROUTER = "ipfs_embeddings_router"
    IPFS_CONTENT_ROUTER = "ipfs_content_router"
    MCP_REMOTE = "mcp_remote"
    COMPOSITE = "composite"


class AIExecutionMode(str, Enum):
    """Supported execution modes for AI capabilities."""

    FIXTURE = "fixture"
    DIRECT_IMPORT = "direct_import"
    CLI_LIVE = "cli_live"
    API_LIVE = "api_live"
    MCP_REMOTE = "mcp_remote"
    ORCHESTRATED = "orchestrated"


@dataclass(frozen=True)
class AICapabilitySpec:
    """Static metadata for a single AI capability."""

    capability_id: str
    title: str
    description: str
    backend_family: AIBackendFamily
    execution_modes: tuple[AIExecutionMode, ...]
    required_inputs: tuple[str, ...] = ()
    optional_inputs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    read_only: bool = True


@dataclass
class AICapabilityResult:
    """Normalized AI capability execution result."""

    capability_id: str
    backend_family: AIBackendFamily
    execution_mode: AIExecutionMode
    ok: bool
    output: Any = None
    error: str | None = None
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIRequestContext:
    """Shared context carried across AI capability requests."""

    repo: str | None = None
    pr_number: int | None = None
    workflow_name: str | None = None
    check_name: str | None = None
    failure_target: str | None = None
    failure_target_type: str | None = None
    session_id: str | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class AICapabilityRequest:
    """Typed AI capability request for router and planner integration."""

    capability_id: str
    context: AIRequestContext = field(default_factory=AIRequestContext)
    inputs: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
