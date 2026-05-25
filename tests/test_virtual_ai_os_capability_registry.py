"""Tests for the virtual AI OS capability registry."""

from handsfree.ai import (
    CapabilityExecutionMode,
    build_virtual_ai_os_execution_matrix,
    get_virtual_ai_os_capability,
    list_virtual_ai_os_capabilities,
    resolve_virtual_ai_os_execution_mode,
)
from handsfree.capability_registry import (
    CAPABILITY_ROUTING_SURFACE_LABELS,
    CapabilityRegistry,
    list_capability_routing_surfaces,
)


def test_virtual_ai_os_registry_exposes_initial_capability_set():
    capability_ids = [entry.capability_id for entry in list_virtual_ai_os_capabilities()]

    assert capability_ids == [
        "agentic_fetch",
        "dataset_discovery",
        "embedding",
        "ipfs_pin",
        "storage",
        "workflow",
    ]


def test_virtual_ai_os_registry_includes_cross_repo_metadata():
    embedding = get_virtual_ai_os_capability("embedding")

    assert embedding.owner_repo == "endomorphosis/ipfs_datasets_py"
    assert embedding.provider_name == "ipfs_datasets_mcp"
    assert embedding.server_family == "ipfs_datasets"
    assert embedding.default_execution_mode == CapabilityExecutionMode.DIRECT_IMPORT
    assert embedding.fallback_execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert embedding.artifact_output == ("embedding_vector", "embedding_dimensions")
    assert "tests/test_virtual_ai_os_capability_registry.py" in embedding.integration_test_ids


def test_virtual_ai_os_registry_resolves_legacy_capability_aliases():
    entry = get_virtual_ai_os_capability("ipfs.embeddings.embed_text")

    assert entry.capability_id == "embedding"


def test_virtual_ai_os_execution_mode_resolution_is_deterministic():
    assert (
        resolve_virtual_ai_os_execution_mode("embedding")
        == CapabilityExecutionMode.DIRECT_IMPORT
    )
    assert (
        resolve_virtual_ai_os_execution_mode(
            "embedding",
            provider_preferred_modes=(CapabilityExecutionMode.MCP_REMOTE,),
        )
        == CapabilityExecutionMode.MCP_REMOTE
    )
    assert (
        resolve_virtual_ai_os_execution_mode(
            "ipfs_pin",
            requested_mode=CapabilityExecutionMode.DIRECT_CLI,
        )
        == CapabilityExecutionMode.DIRECT_CLI
    )


def test_virtual_ai_os_execution_mode_resolution_rejects_unsupported_mode():
    try:
        resolve_virtual_ai_os_execution_mode(
            "dataset_discovery",
            requested_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        )
    except ValueError as exc:
        assert "does not support execution mode" in str(exc)
    else:
        raise AssertionError("Expected unsupported execution mode to fail")


def test_virtual_ai_os_execution_matrix_tracks_mcp_alignment():
    matrix = {row["capability_id"]: row for row in build_virtual_ai_os_execution_matrix()}

    assert matrix["embedding"]["mcp_capability_registered"] is True
    assert matrix["dataset_discovery"]["mcp_capability_registered"] is True
    assert matrix["storage"]["default_execution_mode"] == "mcp_remote"
    assert matrix["workflow"]["fallback_execution_mode"] == "orchestrated"


def test_top_level_capability_registry_path_resolves_stable_ids():
    registry = CapabilityRegistry()

    assert registry.get("ipfs.embeddings.embed_text").capability_id == "embedding"
    assert (
        registry.resolve_execution_mode("embedding", provider_preferred_modes=("mcp_remote",))
        == CapabilityExecutionMode.MCP_REMOTE
    )
    assert [entry.capability_id for entry in registry.list_capabilities()] == [
        "agentic_fetch",
        "dataset_discovery",
        "embedding",
        "ipfs_pin",
        "storage",
        "workflow",
    ]


def test_capability_routing_surface_catalog_names_virtual_ai_os_surfaces():
    surfaces = {surface.surface_id: surface for surface in list_capability_routing_surfaces()}

    assert set(surfaces) == set(CAPABILITY_ROUTING_SURFACE_LABELS)
    assert surfaces["local_python"].label == "local Python"
    assert surfaces["daemon_task"].label == "daemon tasks"
    assert surfaces["mcp_mcp_plus_plus"].label == "MCP/MCP++"
    assert surfaces["swissknife_orb"].label == "SwissKnife ORB"
    assert surfaces["hallucinate_app"].label == "Hallucinate App"
    assert surfaces["mobile_glasses"].label == "mobile/glasses"
