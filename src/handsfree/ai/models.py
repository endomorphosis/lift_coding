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
    IPFS_ACCELERATE = "ipfs_accelerate"
    IPFS_KIT = "ipfs_kit"
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


class CapabilityExecutionMode(str, Enum):
    """Cross-repo execution modes used by the virtual AI OS registry."""

    DIRECT_IMPORT = "direct_import"
    DIRECT_CLI = "direct_cli"
    MCP_REMOTE = "mcp_remote"
    ORCHESTRATED = "orchestrated"


class CapabilityConfirmationPolicy(str, Enum):
    """Normalized confirmation policy for cross-repo capabilities."""

    SAFE_READ = "safe_read"
    SAFE_WRITE = "safe_write"
    REQUIRE_CONFIRMATION = "require_confirmation"
    PROVIDER_DEFAULT = "provider_default"


class CapabilityRuntimeSurface(str, Enum):
    """Execution surface selected by the virtual AI OS runtime router."""

    DIRECT_ADAPTER = "direct_adapter"
    LOCAL_CLI = "local_cli"
    MCP_PROVIDER = "mcp_provider"
    DAEMON_MEDIATED = "daemon_mediated"
    SWISSKNIFE_ORB = "swissknife_orb"


@dataclass(frozen=True)
class AICapabilityRegistryEntry:
    """Cross-repo capability metadata for the virtual AI OS control plane."""

    capability_id: str
    owner_repo: str
    provider_name: str
    server_family: str
    title: str
    description: str
    execution_modes: tuple[CapabilityExecutionMode, ...]
    default_execution_mode: CapabilityExecutionMode
    fallback_execution_mode: CapabilityExecutionMode | None
    confirmation_policy: CapabilityConfirmationPolicy
    input_schema_ref: str
    result_schema_ref: str
    artifact_output: tuple[str, ...] = ()
    display_summary_fields: tuple[str, ...] = ()
    integration_test_ids: tuple[str, ...] = ()
    legacy_capability_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AICapabilityRoute:
    """Deterministic routing decision for a cross-repo capability."""

    capability_id: str
    owner_repo: str
    provider_name: str
    server_family: str
    execution_mode: CapabilityExecutionMode
    runtime_surface: CapabilityRuntimeSurface
    confirmation_policy: CapabilityConfirmationPolicy
    handler_ref: str
    cli_command: str | None = None
    fallback_execution_mode: CapabilityExecutionMode | None = None


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
