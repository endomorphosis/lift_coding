"""Shared catalog for MCP-backed IPFS providers and capabilities."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


MCPExecutionMode = str


@dataclass(frozen=True)
class MCPCapabilityDescriptor:
    """Stable HandsFree capability metadata for an MCP-backed provider."""

    capability_id: str
    provider_name: str
    server_family: str
    title: str
    description: str
    execution_modes: tuple[MCPExecutionMode, ...] = ("mcp_remote",)
    default_execution_mode: MCPExecutionMode = "mcp_remote"
    confirmation_policy: str = "provider_default"
    input_schema_ref: str | None = None
    result_schema_ref: str | None = None


@dataclass(frozen=True)
class MCPProviderDescriptor:
    """Human and routing metadata for an MCP-backed provider."""

    provider_name: str
    display_name: str
    short_label: str
    server_family: str
    aliases: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    default_capability: str = "general"
    instruction_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)


_PROVIDERS: dict[str, MCPProviderDescriptor] = {
    "ipfs_datasets_mcp": MCPProviderDescriptor(
        provider_name="ipfs_datasets_mcp",
        display_name="IPFS Datasets",
        short_label="datasets",
        server_family="ipfs_datasets",
        aliases=("ipfs datasets", "ipfs dataset"),
        capabilities=("dataset_discovery", "dataset_processing", "embedding", "background_task"),
        default_capability="dataset_discovery",
        instruction_keywords={
            "embedding": ("embed", "embedding", "vector", "similarity", "index"),
            "dataset_processing": ("process", "transform", "convert", "analyze", "audit"),
            "dataset_discovery": ("dataset", "datasets", "find", "search", "discover", "legal"),
            "background_task": ("background", "queue", "task", "schedule"),
        },
    ),
    "ipfs_kit_mcp": MCPProviderDescriptor(
        provider_name="ipfs_kit_mcp",
        display_name="IPFS Kit",
        short_label="kit",
        server_family="ipfs_kit",
        aliases=("ipfs kit",),
        capabilities=("ipfs_add", "ipfs_cat", "ipfs_pin", "storage"),
        default_capability="storage",
        instruction_keywords={
            "ipfs_add": ("add", "upload", "store", "put"),
            "ipfs_cat": ("cat", "fetch", "read", "download", "get"),
            "ipfs_pin": ("pin", "unpin"),
            "storage": ("bucket", "storage", "backend", "config"),
        },
    ),
    "ipfs_accelerate_mcp": MCPProviderDescriptor(
        provider_name="ipfs_accelerate_mcp",
        display_name="IPFS Accelerate",
        short_label="accelerate",
        server_family="ipfs_accelerate",
        aliases=("ipfs accelerate",),
        capabilities=("workflow", "background_task", "p2p", "agentic_fetch"),
        default_capability="workflow",
        instruction_keywords={
            "p2p": ("peer", "p2p", "worker", "distributed"),
            "background_task": ("background", "queue", "task", "schedule"),
            "agentic_fetch": ("fetch", "crawl", "discover", "archive"),
            "workflow": ("workflow", "run", "pipeline", "orchestrate"),
        },
    ),
}


_CAPABILITIES: dict[str, MCPCapabilityDescriptor] = {
    "dataset_discovery": MCPCapabilityDescriptor(
        capability_id="dataset_discovery",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Dataset Discovery",
        description="Discover and expand search queries for datasets through ipfs_datasets tools.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_read",
        input_schema_ref="handsfree.capability.dataset_discovery.input",
        result_schema_ref="handsfree.capability.dataset_discovery.result",
    ),
    "dataset_processing": MCPCapabilityDescriptor(
        capability_id="dataset_processing",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Dataset Processing",
        description="Run dataset transformation and analysis workflows through ipfs_datasets.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.dataset_processing.input",
        result_schema_ref="handsfree.capability.dataset_processing.result",
    ),
    "embedding": MCPCapabilityDescriptor(
        capability_id="embedding",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Embeddings",
        description="Create embeddings and vector-ready representations through ipfs_datasets.",
        execution_modes=("direct_import", "mcp_remote"),
        confirmation_policy="safe_read",
        input_schema_ref="handsfree.capability.embedding.input",
        result_schema_ref="handsfree.capability.embedding.result",
    ),
    "background_task": MCPCapabilityDescriptor(
        capability_id="background_task",
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        title="Background Task",
        description="Submit and poll background tasks through a remote MCP task dispatcher.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.background_task.input",
        result_schema_ref="handsfree.capability.background_task.result",
    ),
    "ipfs_add": MCPCapabilityDescriptor(
        capability_id="ipfs_add",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Add Content",
        description="Add content to IPFS through the IPFS Kit MCP surface.",
        execution_modes=("direct_import", "mcp_remote"),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.ipfs_add.input",
        result_schema_ref="handsfree.capability.ipfs_add.result",
    ),
    "ipfs_cat": MCPCapabilityDescriptor(
        capability_id="ipfs_cat",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Read Content",
        description="Read content from IPFS through the IPFS Kit MCP surface.",
        execution_modes=("direct_import", "mcp_remote"),
        confirmation_policy="safe_read",
        input_schema_ref="handsfree.capability.ipfs_cat.input",
        result_schema_ref="handsfree.capability.ipfs_cat.result",
    ),
    "ipfs_pin": MCPCapabilityDescriptor(
        capability_id="ipfs_pin",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Pin Content",
        description="Pin or unpin content through IPFS Kit with direct or MCP-backed routing.",
        execution_modes=("direct_import", "mcp_remote"),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.ipfs_pin.input",
        result_schema_ref="handsfree.capability.ipfs_pin.result",
    ),
    "storage": MCPCapabilityDescriptor(
        capability_id="storage",
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        title="Storage",
        description="General IPFS storage management capability for IPFS Kit.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.storage.input",
        result_schema_ref="handsfree.capability.storage.result",
    ),
    "workflow": MCPCapabilityDescriptor(
        capability_id="workflow",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Workflow",
        description="Run accelerate workflows through the MCP task dispatcher.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.workflow.input",
        result_schema_ref="handsfree.capability.workflow.result",
    ),
    "p2p": MCPCapabilityDescriptor(
        capability_id="p2p",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Peer To Peer",
        description="Use distributed worker and peer-to-peer accelerate features.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.p2p.input",
        result_schema_ref="handsfree.capability.p2p.result",
    ),
    "agentic_fetch": MCPCapabilityDescriptor(
        capability_id="agentic_fetch",
        provider_name="ipfs_accelerate_mcp",
        server_family="ipfs_accelerate",
        title="Agentic Fetch",
        description="Run discovery and fetch workflows through IPFS Accelerate.",
        execution_modes=("mcp_remote",),
        confirmation_policy="safe_write",
        input_schema_ref="handsfree.capability.agentic_fetch.input",
        result_schema_ref="handsfree.capability.agentic_fetch.result",
    ),
}


_ALIASES = {
    alias: descriptor.provider_name
    for descriptor in _PROVIDERS.values()
    for alias in descriptor.aliases
}

_SERVER_FAMILY_TO_PROVIDER = {
    descriptor.server_family: descriptor.provider_name
    for descriptor in _PROVIDERS.values()
}

_SERVER_FAMILY_ENV_PREFIX = {
    "ipfs_datasets": "HANDSFREE_MCP_IPFS_DATASETS",
    "ipfs_kit": "HANDSFREE_MCP_IPFS_KIT",
    "ipfs_accelerate": "HANDSFREE_MCP_IPFS_ACCELERATE",
}


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _allow_direct_execution(provider_name: str) -> bool:
    descriptor = get_provider_descriptor(provider_name)
    if descriptor is None:
        return _env_flag("HANDSFREE_MCP_ALLOW_DIRECT_EXECUTION", True)

    prefix = _SERVER_FAMILY_ENV_PREFIX.get(descriptor.server_family)
    if not _env_flag("HANDSFREE_MCP_ALLOW_DIRECT_EXECUTION", True):
        return False
    if prefix is None:
        return True
    return _env_flag(f"{prefix}_ALLOW_DIRECT_EXECUTION", True)


def get_provider_descriptor(provider_name: str) -> MCPProviderDescriptor | None:
    """Return MCP descriptor for a provider name."""
    return _PROVIDERS.get(provider_name)


def get_capability_descriptor(capability_id: str) -> MCPCapabilityDescriptor | None:
    """Return metadata for a canonical MCP capability identifier."""
    return _CAPABILITIES.get(capability_id.strip().lower())


def get_provider_capabilities(provider_name: str) -> tuple[MCPCapabilityDescriptor, ...]:
    """Return canonical capability descriptors for the provider."""
    descriptor = get_provider_descriptor(provider_name)
    if descriptor is None:
        return ()
    return tuple(
        capability_descriptor
        for capability_id in descriptor.capabilities
        if (capability_descriptor := get_capability_descriptor(capability_id)) is not None
    )


def resolve_provider_alias(alias: str) -> str | None:
    """Resolve human alias text to provider name."""
    return _ALIASES.get(alias.strip().lower())


def resolve_provider_name_for_server_family(server_family: str) -> str | None:
    """Resolve a configured MCP server family to its canonical provider name."""
    return _SERVER_FAMILY_TO_PROVIDER.get(server_family.strip().lower())


def provider_supports_capability(provider_name: str, capability_id: str) -> bool:
    """Return whether the provider owns the canonical capability."""
    descriptor = get_capability_descriptor(capability_id)
    return descriptor is not None and descriptor.provider_name == provider_name


def infer_provider_capability(provider_name: str, instruction: str | None) -> str | None:
    """Infer the likely MCP capability for an instruction."""
    descriptor = get_provider_descriptor(provider_name)
    if descriptor is None:
        return None
    normalized = (instruction or "").strip().lower()
    if not normalized:
        return descriptor.default_capability

    for capability, keywords in descriptor.instruction_keywords.items():
        if any(keyword in normalized for keyword in keywords):
            return capability
    return descriptor.default_capability


def resolve_provider_capability(
    provider_name: str,
    requested_capability: str | None = None,
    instruction: str | None = None,
) -> str | None:
    """Resolve the canonical capability for a provider request.

    If an explicit capability is supplied, it must belong to the provider or
    `None` is returned. Otherwise the provider's keyword inference is used.
    """
    normalized_requested = (requested_capability or "").strip().lower()
    if normalized_requested:
        if provider_supports_capability(provider_name, normalized_requested):
            return normalized_requested
        return None
    return infer_provider_capability(provider_name, instruction)


def resolve_capability_execution_mode(
    provider_name: str,
    capability_id: str | None,
    preferred_mode: str | None = None,
) -> str | None:
    """Resolve the preferred execution mode for a provider capability."""
    if capability_id is None:
        return None

    descriptor = get_capability_descriptor(capability_id)
    if descriptor is None or descriptor.provider_name != provider_name:
        return None

    allowed_modes = descriptor.execution_modes
    if not _allow_direct_execution(provider_name):
        allowed_modes = tuple(mode for mode in descriptor.execution_modes if mode != "direct_import")
    if not allowed_modes:
        return None

    normalized_mode = (preferred_mode or "").strip().lower()
    if normalized_mode and normalized_mode in allowed_modes:
        return normalized_mode
    if descriptor.default_execution_mode in allowed_modes:
        return descriptor.default_execution_mode
    return allowed_modes[0]
