"""Cross-repo capability registry for the virtual AI OS control plane."""

from __future__ import annotations

from handsfree.mcp.catalog import get_capability_descriptor

from .models import (
    AICapabilityRegistryEntry,
    CapabilityConfirmationPolicy,
    CapabilityExecutionMode,
)


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
        artifact_output=("embedding_vector", "embedding_dimensions"),
        display_summary_fields=("summary", "vector_count", "model"),
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
        artifact_output=("cid", "receipt_ref"),
        display_summary_fields=("summary", "cid", "pin_status"),
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
        artifact_output=("result_cid", "event_dag_ref", "run_id"),
        display_summary_fields=("summary", "status", "run_id"),
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
        artifact_output=("result_cid", "fetch_manifest"),
        display_summary_fields=("summary", "status", "source_count"),
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
        artifact_output=("result_cid", "dataset_manifest"),
        display_summary_fields=("summary", "dataset_count", "query"),
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
        artifact_output=("result_cid", "package_ref", "receipt_ref"),
        display_summary_fields=("summary", "status", "result_cid"),
        integration_test_ids=("tests/test_virtual_ai_os_capability_registry.py",),
        legacy_capability_ids=("storage", "ipfs.content.add_bytes", "ipfs.content.read_ai_output"),
    ),
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
                "integration_test_ids": entry.integration_test_ids,
                "input_schema_ref": entry.input_schema_ref,
                "result_schema_ref": entry.result_schema_ref,
                "mcp_capability_registered": mcp_descriptor is not None,
            }
        )
    return rows


def _normalize_mode(value: str | CapabilityExecutionMode | None) -> CapabilityExecutionMode | None:
    if value is None:
        return None
    if isinstance(value, CapabilityExecutionMode):
        return value
    normalized = value.strip().lower()
    if not normalized:
        return None
    return CapabilityExecutionMode(normalized)
