"""Typed models for shared AI capability routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any


class AIBackendFamily(StrEnum):
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


class AIExecutionMode(StrEnum):
    """Supported execution modes for AI capabilities."""

    FIXTURE = "fixture"
    DIRECT_IMPORT = "direct_import"
    CLI_LIVE = "cli_live"
    API_LIVE = "api_live"
    MCP_REMOTE = "mcp_remote"
    ORCHESTRATED = "orchestrated"


class CapabilityExecutionMode(StrEnum):
    """Cross-repo execution modes used by the virtual AI OS registry."""

    DIRECT_IMPORT = "direct_import"
    DIRECT_CLI = "direct_cli"
    MCP_REMOTE = "mcp_remote"
    ORCHESTRATED = "orchestrated"


class CapabilityConfirmationPolicy(StrEnum):
    """Normalized confirmation policy for cross-repo capabilities."""

    SAFE_READ = "safe_read"
    SAFE_WRITE = "safe_write"
    REQUIRE_CONFIRMATION = "require_confirmation"
    PROVIDER_DEFAULT = "provider_default"


class CapabilityRuntimeSurface(StrEnum):
    """Execution surface selected by the virtual AI OS runtime router."""

    DIRECT_ADAPTER = "direct_adapter"
    LOCAL_CLI = "local_cli"
    MCP_PROVIDER = "mcp_provider"
    DAEMON_MEDIATED = "daemon_mediated"
    SWISSKNIFE_ORB = "swissknife_orb"
    HALLUCINATE_APP = "hallucinate_app"


class CapabilityPlacementLayer(str, Enum):
    """Virtual runtime layer that owns an execution placement decision."""

    SEMANTIC_ROUTING = "semantic_routing"
    EXECUTION_ACCELERATION = "execution_acceleration"
    CONTENT_PROVENANCE = "content_provenance"
    HANDSFREE_DAEMON = "handsfree_daemon"
    MCP_PROTOCOL = "mcp_protocol"
    SWISSKNIFE_ORB = "swissknife_orb"


@dataclass(frozen=True)
class AICapabilityRuntimePlacement:
    """Deterministic placement decision for a virtual AI OS runtime route."""

    capability_id: str
    execution_mode: CapabilityExecutionMode
    runtime_surface: CapabilityRuntimeSurface
    supported_surfaces: tuple[CapabilityRuntimeSurface, ...]
    fallback_surfaces: tuple[CapabilityRuntimeSurface, ...] = ()
    placement_layer: CapabilityPlacementLayer | None = None
    target_repo: str | None = None
    reason: str | None = None
    constraints: tuple[str, ...] = ()


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
    voice_formatter: str
    follow_up_action_builder: str
    artifact_output: tuple[str, ...] = ()
    display_summary_fields: tuple[str, ...] = ()
    voice_display_summary_formatter_ref: str | None = None
    integration_test_ids: tuple[str, ...] = ()
    legacy_capability_ids: tuple[str, ...] = ()
    command_envelope_fields: tuple[str, ...] = ()
    receipt_fields: tuple[str, ...] = ()
    supported_surface_ids: tuple[str, ...] = ()
    fallback_render_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class AICapabilityArtifactRefs:
    """Artifact and provenance references produced by a capability execution."""

    result_cid: str | None = None
    receipt_ref: str | None = None
    event_dag_ref: str | None = None
    delegation_ref: str | None = None


@dataclass(frozen=True)
class AICapabilityExecutionTrace:
    """Trace metadata shared by direct, CLI, and MCP-backed capability routes."""

    request_id: str | None = None
    run_id: str | None = None
    tool_name: str | None = None
    remote_task_id: str | None = None
    last_protocol_state: str | None = None


@dataclass(frozen=True)
class AICapabilityResultEnvelope:
    """Normalized result envelope for cross-repo virtual AI OS capabilities."""

    capability_id: str
    provider: str
    server_family: str
    execution_mode: CapabilityExecutionMode
    status: str
    spoken_text: str
    summary: str
    structured_output: Any = None
    follow_up_actions: tuple[dict[str, Any], ...] = ()
    trace: AICapabilityExecutionTrace = field(default_factory=AICapabilityExecutionTrace)
    artifact_refs: AICapabilityArtifactRefs = field(default_factory=AICapabilityArtifactRefs)

    def as_dict(self) -> dict[str, Any]:
        """Return the normalized envelope as JSON-serializable data."""
        return {
            "capability_id": self.capability_id,
            "provider": self.provider,
            "server_family": self.server_family,
            "execution_mode": self.execution_mode.value,
            "status": self.status,
            "spoken_text": self.spoken_text,
            "summary": self.summary,
            "structured_output": self.structured_output,
            "follow_up_actions": list(self.follow_up_actions),
            "trace": {
                "request_id": self.trace.request_id,
                "run_id": self.trace.run_id,
                "tool_name": self.trace.tool_name,
                "remote_task_id": self.trace.remote_task_id,
                "last_protocol_state": self.trace.last_protocol_state,
            },
            "artifact_refs": {
                "result_cid": self.artifact_refs.result_cid,
                "receipt_ref": self.artifact_refs.receipt_ref,
                "event_dag_ref": self.artifact_refs.event_dag_ref,
                "delegation_ref": self.artifact_refs.delegation_ref,
            },
        }


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
    placement_layer: CapabilityPlacementLayer | None = None
    placement_target: str | None = None
    placement_reason: str | None = None
    placement_constraints: tuple[str, ...] = ()


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
