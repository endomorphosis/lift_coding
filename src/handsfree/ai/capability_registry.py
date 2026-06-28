"""Cross-repo capability registry for the virtual AI OS control plane."""

from __future__ import annotations

from handsfree.mcp.catalog import get_capability_descriptor

from .models import (
    AICapabilityArtifactRefs,
    AICapabilityExecutionTrace,
    AICapabilityRegistryEntry,
    AICapabilityResultEnvelope,
    CapabilityConfirmationPolicy,
    CapabilityExecutionMode,
)

_GLASSES_WIDGET_COMMAND_ENVELOPE_FIELDS = (
    "capability_id",
    "command_id",
    "session_id",
    "desktop_id",
    "phone_host_id",
    "widget_kind",
    "descriptor_cid",
    "manifest_cid",
    "correlation_id",
    "operator_id",
    "action",
    "payload",
    "policy",
    "placement",
    "fallback",
)

_GLASSES_WIDGET_RECEIPT_FIELDS = (
    "capability_receipt_cid",
    "orb_receipt_cid",
    "bridge_receipt_cid",
    "policy_receipt_cid",
    "placement_receipt_cid",
    "transfer_receipt_cid",
    "fallback_receipt_cid",
    "validation_receipt_cid",
    "render_result",
)

_GLASSES_WIDGET_SURFACES = (
    "swissknife_orb",
    "hallucinate_app",
    "mobile_glasses",
    "meta_glasses_display",
)

_GLASSES_WIDGET_FALLBACK_RENDER_PATHS = (
    "mobile-card",
    "display_webapp",
    "simulator",
)

_GLASSES_WIDGET_INTEGRATION_TESTS = (
    "tests/test_virtual_ai_os_capability_registry.py",
    "tests/test_meta_glasses_display_todo_queue.py",
)

_GLASSES_WIDGET_ACTIONS = {
    "render": (
        "Render Glasses Widget",
        "Create or replace the current handsfree.virtual-desktop-session manifest.",
    ),
    "update": (
        "Update Glasses Widget",
        "Apply a bounded state patch to the active virtual desktop session widget.",
    ),
    "confirm": (
        "Confirm Glasses Widget Action",
        "Submit a policy-approved confirmation action from the widget prompt surface.",
    ),
    "cancel": (
        "Cancel Glasses Widget Action",
        "Cancel the active widget action, offload transfer, or virtual desktop command.",
    ),
}


_REGISTRY: dict[str, AICapabilityRegistryEntry] = {
    "embedding": AICapabilityRegistryEntry(
        capability_id="embedding",
        owner_repo="endomorphosis/ipfs_datasets_py",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Embeddings",
        description=(
            "Create vector representations through ipfs_datasets_py with one canonical "
            "control-plane capability shared by direct-import and MCP-backed routing."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_READ,
        input_schema_ref="handsfree.capability.embedding.input",
        result_schema_ref="handsfree.capability.embedding.result",
        voice_formatter="handsfree.ai.formatters:format_embedding_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_embedding_actions",
        artifact_output=("embedding_vector", "embedding_dimensions"),
        display_summary_fields=("summary", "vector_count", "model"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_embedding",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/test_ai_capabilities.py",
        ),
        legacy_capability_ids=(
            "embedding",
            "ipfs.embeddings.embed_text",
            "ipfs.embeddings.embed_texts",
        ),
    ),
    "ipfs_pin": AICapabilityRegistryEntry(
        capability_id="ipfs_pin",
        owner_repo="endomorphosis/ipfs_kit_py",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Pin Content",
        description=(
            "Pin or unpin content through ipfs_kit_py with a shared capability that maps "
            "both direct-import and remote execution paths."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.DIRECT_CLI,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.ipfs_pin.input",
        result_schema_ref="handsfree.capability.ipfs_pin.result",
        voice_formatter="handsfree.ai.formatters:format_ipfs_pin_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_ipfs_pin_actions",
        artifact_output=("cid", "receipt_ref"),
        display_summary_fields=("summary", "cid", "pin_status"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_ipfs_pin",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/test_ai_capabilities.py",
        ),
        legacy_capability_ids=("ipfs_pin", "ipfs.kit.pin", "ipfs.kit.unpin"),
    ),
    "workflow": AICapabilityRegistryEntry(
        capability_id="workflow",
        owner_repo="endomorphosis/ipfs_accelerate_py",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Workflow",
        description=(
            "Run multi-step accelerate workflows through the shared runtime control plane."
        ),
        execution_modes=(
            CapabilityExecutionMode.ORCHESTRATED,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.ORCHESTRATED,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.workflow.input",
        result_schema_ref="handsfree.capability.workflow.result",
        voice_formatter="handsfree.ai.formatters:format_workflow_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_workflow_actions",
        artifact_output=("result_cid", "event_dag_ref", "run_id"),
        display_summary_fields=("summary", "status", "run_id"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_workflow",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("workflow",),
    ),
    "agentic_fetch": AICapabilityRegistryEntry(
        capability_id="agentic_fetch",
        owner_repo="endomorphosis/ipfs_accelerate_py",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Agentic Fetch",
        description=(
            "Run discovery and fetch workflows through ipfs_accelerate_py with a single "
            "capability contract for planner and task routing."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_CLI,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.DIRECT_CLI,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.agentic_fetch.input",
        result_schema_ref="handsfree.capability.agentic_fetch.result",
        voice_formatter="handsfree.ai.formatters:format_agentic_fetch_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_agentic_fetch_actions",
        artifact_output=("result_cid", "fetch_manifest"),
        display_summary_fields=("summary", "status", "source_count"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_agentic_fetch",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("agentic_fetch",),
    ),
    "dataset_discovery": AICapabilityRegistryEntry(
        capability_id="dataset_discovery",
        owner_repo="endomorphosis/ipfs_datasets_py",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Dataset Discovery",
        description=(
            "Discover datasets through ipfs_datasets_py using one registry entry shared by "
            "planner, task, and voice/display surfaces."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_CLI,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.DIRECT_CLI,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_READ,
        input_schema_ref="handsfree.capability.dataset_discovery.input",
        result_schema_ref="handsfree.capability.dataset_discovery.result",
        voice_formatter="handsfree.ai.formatters:format_dataset_discovery_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_dataset_discovery_actions",
        artifact_output=("result_cid", "dataset_manifest"),
        display_summary_fields=("summary", "dataset_count", "query"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_dataset_discovery",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("dataset_discovery",),
    ),
    "storage": AICapabilityRegistryEntry(
        capability_id="storage",
        owner_repo="endomorphosis/ipfs_kit_py",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Storage",
        description=(
            "Manage stored artifacts and packaging through ipfs_kit_py behind one "
            "normalized storage capability."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_CLI,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.DIRECT_CLI,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.storage.input",
        result_schema_ref="handsfree.capability.storage.result",
        voice_formatter="handsfree.ai.formatters:format_storage_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_storage_actions",
        artifact_output=("result_cid", "package_ref", "receipt_ref"),
        display_summary_fields=("summary", "status", "result_cid"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_storage",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("storage", "ipfs.content.add_bytes", "ipfs.content.read_ai_output"),
    ),
    "ipfs_add_content": AICapabilityRegistryEntry(
        capability_id="ipfs_add_content",
        owner_repo="endomorphosis/ipfs_kit_py",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="IPFS Add Content",
        description=(
            "Add content to IPFS through ipfs_kit_py, returning a content-addressed CID. "
            "Supports both file and bytes input with optional pinning."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.ipfs_add_content.input",
        result_schema_ref="handsfree.capability.ipfs_add_content.result",
        voice_formatter="handsfree.ai.formatters:format_ipfs_add_content_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_ipfs_add_content_actions",
        artifact_output=("cid", "size", "receipt_ref"),
        display_summary_fields=("summary", "cid", "size"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_ipfs_add_content",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/integration/test_ipfs_backend_integration.py",
        ),
        legacy_capability_ids=(
            "ipfs_add_content",
            "ipfs.kit.add",
            "ipfs.content.add",
            "storage.add_content",
        ),
    ),
    "ipfs_get_content": AICapabilityRegistryEntry(
        capability_id="ipfs_get_content",
        owner_repo="endomorphosis/ipfs_kit_py",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="IPFS Get Content",
        description=(
            "Retrieve content from IPFS by CID through ipfs_kit_py. "
            "Falls back to ipfs_datasets_py routers when kit is unavailable."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_READ,
        input_schema_ref="handsfree.capability.ipfs_get_content.input",
        result_schema_ref="handsfree.capability.ipfs_get_content.result",
        voice_formatter="handsfree.ai.formatters:format_ipfs_get_content_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_ipfs_get_content_actions",
        artifact_output=("cid", "data_size", "content_type"),
        display_summary_fields=("summary", "cid", "data_size"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_ipfs_get_content",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/integration/test_ipfs_backend_integration.py",
        ),
        legacy_capability_ids=(
            "ipfs_get_content",
            "ipfs.kit.cat",
            "ipfs.content.get",
            "storage.get_content",
        ),
    ),
    "hardware_profile": AICapabilityRegistryEntry(
        capability_id="hardware_profile",
        owner_repo="endomorphosis/ipfs_accelerate_py",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Hardware Profile",
        description=(
            "Discover available hardware acceleration capabilities through "
            "ipfs_accelerate_py including WebNN, WebGPU, and CUDA support."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_READ,
        input_schema_ref="handsfree.capability.hardware_profile.input",
        result_schema_ref="handsfree.capability.hardware_profile.result",
        voice_formatter="handsfree.ai.formatters:format_hardware_profile_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_hardware_profile_actions",
        artifact_output=("capabilities", "device_count", "accelerators"),
        display_summary_fields=("summary", "device_count", "capabilities"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_hardware_profile",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/integration/test_ipfs_backend_integration.py",
        ),
        legacy_capability_ids=(
            "hardware_profile",
            "compute.hardware_profile",
            "ipfs.accelerate.capabilities",
        ),
    ),
    "inference": AICapabilityRegistryEntry(
        capability_id="inference",
        owner_repo="endomorphosis/ipfs_accelerate_py",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Model Inference",
        description=(
            "Run model inference through ipfs_accelerate_py with hardware-optimized "
            "execution. Supports text generation, embeddings, and custom model pipelines."
        ),
        execution_modes=(
            CapabilityExecutionMode.DIRECT_IMPORT,
            CapabilityExecutionMode.MCP_REMOTE,
            CapabilityExecutionMode.ORCHESTRATED,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.inference.input",
        result_schema_ref="handsfree.capability.inference.result",
        voice_formatter="handsfree.ai.formatters:format_inference_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_inference_actions",
        artifact_output=("result", "model_name", "run_id", "receipt_cid"),
        display_summary_fields=("summary", "model_name", "status"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_inference",
        integration_test_ids=(
            "tests/test_virtual_ai_os_capability_registry.py",
            "tests/integration/test_ipfs_backend_integration.py",
        ),
        legacy_capability_ids=(
            "inference",
            "compute.run_inference",
            "ipfs.accelerate.run_model",
        ),
    ),
    "llm_generation": AICapabilityRegistryEntry(
        capability_id="llm_generation",
        owner_repo="handsfree",
        provider_name="handsfree_ai_router",
        server_family="handsfree_ai",
        title="LLM Generation",
        description=(
            "Generate and revise model output through the HandsFree AI router while "
            "preserving one dispatch contract for planner, daemon, and MCP callers."
        ),
        execution_modes=(
            CapabilityExecutionMode.ORCHESTRATED,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.ORCHESTRATED,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_READ,
        input_schema_ref="handsfree.capability.llm_generation.input",
        result_schema_ref="handsfree.capability.llm_generation.result",
        voice_formatter="handsfree.ai.formatters:format_llm_generation_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_llm_generation_actions",
        artifact_output=("response_text", "revision_ref", "model_trace_ref"),
        display_summary_fields=("summary", "model", "status"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_llm_generation",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("llm_generation", "llm.revision", "ai.generate"),
    ),
    "ui_render_session": AICapabilityRegistryEntry(
        capability_id="ui_render_session",
        owner_repo="endomorphosis/swissknife",
        provider_name="swissknife_orb",
        server_family="swissknife",
        title="UI Render Session",
        description=(
            "Create and update ORB-backed UI render sessions that can be mirrored by "
            "Hallucinate App and the mobile/glasses presentation surfaces."
        ),
        execution_modes=(
            CapabilityExecutionMode.MCP_REMOTE,
            CapabilityExecutionMode.ORCHESTRATED,
        ),
        default_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        fallback_execution_mode=CapabilityExecutionMode.ORCHESTRATED,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.ui_render_session.input",
        result_schema_ref="handsfree.capability.ui_render_session.result",
        voice_formatter="handsfree.ai.formatters:format_ui_render_session_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_ui_render_session_actions",
        artifact_output=("descriptor_ref", "render_session_id", "receipt_ref"),
        display_summary_fields=("summary", "surface", "render_session_id"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_ui_render_session",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("ui_render_session", "orb.render_session"),
    ),
    "device_render_transport": AICapabilityRegistryEntry(
        capability_id="device_render_transport",
        owner_repo="handsfree/mobile",
        provider_name="handsfree_mobile_orb",
        server_family="meta_glasses_mobile_orb",
        title="Device Render Transport",
        description=(
            "Route display, action receipts, and transport state to mobile and Meta "
            "glasses endpoints through the shared ORB bridge contract."
        ),
        execution_modes=(
            CapabilityExecutionMode.ORCHESTRATED,
            CapabilityExecutionMode.MCP_REMOTE,
        ),
        default_execution_mode=CapabilityExecutionMode.ORCHESTRATED,
        fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        confirmation_policy=CapabilityConfirmationPolicy.SAFE_WRITE,
        input_schema_ref="handsfree.capability.device_render_transport.input",
        result_schema_ref="handsfree.capability.device_render_transport.result",
        voice_formatter="handsfree.ai.formatters:format_device_render_transport_summary",
        follow_up_action_builder="handsfree.ai.follow_up_actions:build_device_render_transport_actions",
        artifact_output=("edge_session_id", "display_receipt_ref", "action_receipt_ref"),
        display_summary_fields=("summary", "edge_id", "status"),
        voice_display_summary_formatter_ref="handsfree.capability_summaries:format_device_render_transport",
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("device_render_transport", "meta_glasses.render_transport"),
    ),
    **{
        f"vai.glasses_widget.{action}": AICapabilityRegistryEntry(
            capability_id=f"vai.glasses_widget.{action}",
            owner_repo="handsfree/mobile",
            provider_name="handsfree_mobile_display_widget",
            server_family="meta_glasses_mobile_orb",
            title=title,
            description=(
                f"{description} Swissknife ORB, HandsFree mobile, Meta glasses, "
                "and Hallucinate App share one receipt-backed command envelope."
            ),
            execution_modes=(
                CapabilityExecutionMode.ORCHESTRATED,
                CapabilityExecutionMode.MCP_REMOTE,
            ),
            default_execution_mode=CapabilityExecutionMode.ORCHESTRATED,
            fallback_execution_mode=CapabilityExecutionMode.MCP_REMOTE,
            confirmation_policy=(
                CapabilityConfirmationPolicy.REQUIRE_CONFIRMATION
                if action == "confirm"
                else CapabilityConfirmationPolicy.SAFE_WRITE
            ),
            input_schema_ref=f"handsfree.capability.vai.glasses_widget.{action}.input",
            result_schema_ref=f"handsfree.capability.vai.glasses_widget.{action}.result",
            voice_formatter=(
                f"handsfree.ai.formatters:format_glasses_widget_{action}_summary"
            ),
            follow_up_action_builder=(
                f"handsfree.ai.follow_up_actions:build_glasses_widget_{action}_actions"
            ),
            artifact_output=(
                "capability_receipt_cid",
                "manifest_cid",
                "bridge_receipt_cid",
                "render_result",
            ),
            display_summary_fields=(
                "summary",
                "render_result",
                "fallback.render_path",
                "capability_receipt_cid",
            ),
            voice_display_summary_formatter_ref=(
                "handsfree.capability_summaries:format_glasses_widget"
            ),
            integration_test_ids=_GLASSES_WIDGET_INTEGRATION_TESTS,
            legacy_capability_ids=(
                f"vai.glasses_widget.{action}",
                f"handsfree.mobile_display_widget.{action}",
                f"meta_glasses.widget.{action}",
            ),
            command_envelope_fields=_GLASSES_WIDGET_COMMAND_ENVELOPE_FIELDS,
            receipt_fields=_GLASSES_WIDGET_RECEIPT_FIELDS,
            supported_surface_ids=_GLASSES_WIDGET_SURFACES,
            fallback_render_paths=_GLASSES_WIDGET_FALLBACK_RENDER_PATHS,
        )
        for action, (title, description) in _GLASSES_WIDGET_ACTIONS.items()
    },
}

_ALIASES = {
    legacy_id: capability_id
    for capability_id, entry in _REGISTRY.items()
    for legacy_id in entry.legacy_capability_ids
}


def list_virtual_ai_os_capabilities() -> list[AICapabilityRegistryEntry]:
    """Return the cross-repo capability registry in stable order."""
    return [entry for _, entry in sorted(_REGISTRY.items(), key=lambda item: item[0])]


def get_virtual_ai_os_capability(capability_id: str) -> AICapabilityRegistryEntry:
    """Resolve a canonical or legacy capability identifier."""
    normalized = capability_id.strip().lower()
    canonical = _ALIASES.get(normalized, normalized)
    try:
        return _REGISTRY[canonical]
    except KeyError as exc:
        raise KeyError(f"Unknown virtual AI OS capability: {capability_id}") from exc


def resolve_virtual_ai_os_execution_mode(
    capability_id: str,
    *,
    requested_mode: str | CapabilityExecutionMode | None = None,
    provider_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
    policy_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
    allow_fallback: bool = True,
) -> CapabilityExecutionMode:
    """Resolve execution mode deterministically for a cross-repo capability."""
    entry = get_virtual_ai_os_capability(capability_id)
    supported = set(entry.execution_modes)

    normalized_requested = _normalize_mode(requested_mode)
    if normalized_requested is not None:
        if normalized_requested not in supported:
            raise ValueError(
                f"Capability '{entry.capability_id}' does not support execution mode "
                f"'{normalized_requested.value}'"
            )
        return normalized_requested

    for candidate in provider_preferred_modes:
        normalized = _normalize_mode(candidate)
        if normalized in supported:
            return normalized

    for candidate in policy_preferred_modes:
        normalized = _normalize_mode(candidate)
        if normalized in supported:
            return normalized

    if entry.default_execution_mode in supported:
        return entry.default_execution_mode

    if allow_fallback and entry.fallback_execution_mode in supported:
        return entry.fallback_execution_mode

    raise ValueError(
        f"No supported execution mode available for capability '{entry.capability_id}'"
    )


def build_virtual_ai_os_execution_matrix() -> list[dict[str, object]]:
    """Return a compact execution-matrix view for docs and tests."""
    rows: list[dict[str, object]] = []
    for entry in list_virtual_ai_os_capabilities():
        mcp_descriptor = get_capability_descriptor(entry.capability_id)
        rows.append(
            {
                "capability_id": entry.capability_id,
                "owner_repo": entry.owner_repo,
                "provider_name": entry.provider_name,
                "server_family": entry.server_family,
                "execution_modes": tuple(mode.value for mode in entry.execution_modes),
                "default_execution_mode": entry.default_execution_mode.value,
                "fallback_execution_mode": (
                    entry.fallback_execution_mode.value if entry.fallback_execution_mode else None
                ),
                "confirmation_policy": entry.confirmation_policy.value,
                "artifact_output": entry.artifact_output,
                "display_summary_fields": entry.display_summary_fields,
                "voice_display_summary_formatter_ref": entry.voice_display_summary_formatter_ref,
                "integration_test_ids": entry.integration_test_ids,
                "input_schema_ref": entry.input_schema_ref,
                "result_schema_ref": entry.result_schema_ref,
                "voice_formatter": entry.voice_formatter,
                "follow_up_action_builder": entry.follow_up_action_builder,
                "command_envelope_fields": entry.command_envelope_fields,
                "receipt_fields": entry.receipt_fields,
                "supported_surface_ids": entry.supported_surface_ids,
                "fallback_render_paths": entry.fallback_render_paths,
                "mcp_capability_registered": mcp_descriptor is not None,
            }
        )
    return rows


def build_virtual_ai_os_result_envelope(
    capability_id: str,
    *,
    execution_mode: str | CapabilityExecutionMode | None = None,
    status: str = "completed",
    spoken_text: str | None = None,
    summary: str | None = None,
    structured_output: object | None = None,
    follow_up_actions: tuple[dict[str, object], ...] = (),
    request_id: str | None = None,
    run_id: str | None = None,
    tool_name: str | None = None,
    remote_task_id: str | None = None,
    last_protocol_state: str | None = None,
    result_cid: str | None = None,
    receipt_ref: str | None = None,
    event_dag_ref: str | None = None,
    delegation_ref: str | None = None,
) -> AICapabilityResultEnvelope:
    """Build the normalized result envelope for a registered capability."""
    entry = get_virtual_ai_os_capability(capability_id)
    resolved_mode = _normalize_mode(execution_mode) or entry.default_execution_mode
    if resolved_mode not in set(entry.execution_modes):
        raise ValueError(
            f"Capability '{entry.capability_id}' does not support execution mode "
            f"'{resolved_mode.value}'"
        )
    normalized_status = _normalize_status(status)
    resolved_summary = _resolve_summary(summary, spoken_text, structured_output, normalized_status)
    resolved_spoken_text = (spoken_text or resolved_summary).strip()
    return AICapabilityResultEnvelope(
        capability_id=entry.capability_id,
        provider=entry.provider_name,
        server_family=entry.server_family,
        execution_mode=resolved_mode,
        status=normalized_status,
        spoken_text=resolved_spoken_text,
        summary=resolved_summary,
        structured_output=structured_output if structured_output is not None else {},
        follow_up_actions=tuple(follow_up_actions),
        trace=AICapabilityExecutionTrace(
            request_id=request_id,
            run_id=run_id,
            tool_name=tool_name,
            remote_task_id=remote_task_id,
            last_protocol_state=last_protocol_state or normalized_status,
        ),
        artifact_refs=AICapabilityArtifactRefs(
            result_cid=result_cid or _first_structured_str(structured_output, "result_cid", "cid"),
            receipt_ref=receipt_ref or _first_structured_str(structured_output, "receipt_ref"),
            event_dag_ref=event_dag_ref
            or _first_structured_str(structured_output, "event_dag_ref"),
            delegation_ref=delegation_ref
            or _first_structured_str(structured_output, "delegation_ref"),
        ),
    )


def _normalize_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"completed", "success", "succeeded"}:
        return "completed"
    if normalized in {"needs_input", "requires_input", "awaiting_input"}:
        return "needs_input"
    if normalized in {"failed", "error", "cancelled", "canceled"}:
        return "failed"
    if normalized:
        return "running"
    return "running"


def _resolve_summary(
    summary: str | None,
    spoken_text: str | None,
    structured_output: object | None,
    status: str,
) -> str:
    structured_summary = _first_structured_str(structured_output, "summary", "message")
    for candidate in (summary, spoken_text, structured_summary):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    if status == "completed":
        return "Task completed."
    if status == "needs_input":
        return "I need more information."
    if status == "failed":
        return "Task failed."
    return "Task started."


def _first_structured_str(structured_output: object | None, *keys: str) -> str | None:
    if not isinstance(structured_output, dict):
        return None
    for key in keys:
        value = structured_output.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_mode(value: str | CapabilityExecutionMode | None) -> CapabilityExecutionMode | None:
    if value is None:
        return None
    if isinstance(value, CapabilityExecutionMode):
        return value
    normalized = value.strip().lower()
    if not normalized:
        return None
    return CapabilityExecutionMode(normalized)
