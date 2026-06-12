"""Tests for the virtual AI OS capability registry."""

from importlib import import_module

from handsfree.ai import (
    CapabilityExecutionMode,
    build_virtual_ai_os_execution_matrix,
    build_virtual_ai_os_result_envelope,
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
        "device_render_transport",
        "embedding",
        "ipfs_pin",
        "llm_generation",
        "storage",
        "ui_render_session",
        "workflow",
    ]


def test_virtual_ai_os_registry_includes_cross_repo_metadata():
    embedding = get_virtual_ai_os_capability("embedding")

    assert embedding.owner_repo == "endomorphosis/ipfs_datasets_py"
    assert embedding.provider_name == "ipfs_datasets_mcp"
    assert embedding.server_family == "ipfs_datasets"
    assert embedding.default_execution_mode == CapabilityExecutionMode.DIRECT_IMPORT
    assert embedding.fallback_execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert embedding.voice_formatter == "handsfree.ai.formatters:format_embedding_summary"
    assert (
        embedding.follow_up_action_builder
        == "handsfree.ai.follow_up_actions:build_embedding_actions"
    )
    assert embedding.artifact_output == ("embedding_vector", "embedding_dimensions")
    assert (
        embedding.voice_display_summary_formatter_ref
        == "handsfree.capability_summaries:format_embedding"
    )
    assert "tests/test_virtual_ai_os_capability_registry.py" in embedding.integration_test_ids


def test_virtual_ai_os_registry_defines_formatter_and_follow_up_contracts_for_all_capabilities():
    for entry in list_virtual_ai_os_capabilities():
        assert entry.voice_formatter.startswith("handsfree.ai.formatters:format_")
        assert entry.follow_up_action_builder.startswith(
            "handsfree.ai.follow_up_actions:build_"
        )
        assert entry.input_schema_ref.startswith("handsfree.capability.")
        assert entry.result_schema_ref.startswith("handsfree.capability.")


def test_virtual_ai_os_registry_covers_plan_initial_families():
    capabilities = {entry.capability_id: entry for entry in list_virtual_ai_os_capabilities()}

    assert capabilities["llm_generation"].owner_repo == "handsfree"
    assert capabilities["ui_render_session"].owner_repo == "endomorphosis/swissknife"
    assert capabilities["device_render_transport"].owner_repo == "handsfree/mobile"
    assert capabilities["ui_render_session"].provider_name == "swissknife_orb"
    assert capabilities["device_render_transport"].server_family == "meta_glasses_mobile_orb"
    assert capabilities["llm_generation"].artifact_output == (
        "response_text",
        "revision_ref",
        "model_trace_ref",
    )
    assert capabilities["ui_render_session"].display_summary_fields == (
        "summary",
        "surface",
        "render_session_id",
    )


def test_virtual_ai_os_summary_formatter_refs_are_importable():
    for entry in list_virtual_ai_os_capabilities():
        module_name, function_name = entry.voice_display_summary_formatter_ref.split(":")
        formatter = getattr(import_module(module_name), function_name)

        assert formatter({"summary": f"{entry.capability_id} ready"}) == (
            f"{entry.capability_id} ready"
        )


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
    assert matrix["ipfs_pin"]["voice_formatter"] == (
        "handsfree.ai.formatters:format_ipfs_pin_summary"
    )
    assert matrix["ipfs_pin"]["follow_up_action_builder"] == (
        "handsfree.ai.follow_up_actions:build_ipfs_pin_actions"
    )
    assert (
        matrix["ui_render_session"]["voice_display_summary_formatter_ref"]
        == "handsfree.capability_summaries:format_ui_render_session"
    )


def test_virtual_ai_os_result_envelope_uses_shared_top_level_shape():
    envelope = build_virtual_ai_os_result_envelope(
        "ipfs_pin",
        execution_mode=CapabilityExecutionMode.MCP_REMOTE,
        spoken_text="Pin completed.",
        summary="Pinned CID bafy...",
        structured_output={"cid": "bafy123", "pin_status": "pinned"},
        follow_up_actions=({"id": "read_cid", "label": "Read CID"},),
        request_id="req_123",
        run_id="run_456",
        tool_name="tools_dispatch",
        receipt_ref="receipt_789",
    )

    assert envelope.as_dict() == {
        "capability_id": "ipfs_pin",
        "provider": "ipfs_kit_mcp",
        "server_family": "ipfs_kit",
        "execution_mode": "mcp_remote",
        "status": "completed",
        "spoken_text": "Pin completed.",
        "summary": "Pinned CID bafy...",
        "structured_output": {"cid": "bafy123", "pin_status": "pinned"},
        "follow_up_actions": [{"id": "read_cid", "label": "Read CID"}],
        "trace": {
            "request_id": "req_123",
            "run_id": "run_456",
            "tool_name": "tools_dispatch",
            "remote_task_id": None,
            "last_protocol_state": "completed",
        },
        "artifact_refs": {
            "result_cid": "bafy123",
            "receipt_ref": "receipt_789",
            "event_dag_ref": None,
            "delegation_ref": None,
        },
    }


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
        "device_render_transport",
        "embedding",
        "ipfs_pin",
        "llm_generation",
        "storage",
        "ui_render_session",
        "workflow",
    ]


def test_capability_routing_surface_catalog_names_virtual_ai_os_surfaces():
    surfaces = {surface.surface_id: surface for surface in list_capability_routing_surfaces()}

    assert set(surfaces) == set(CAPABILITY_ROUTING_SURFACE_LABELS)
    assert surfaces["local_python"].label == "local Python"
    assert surfaces["daemon_task"].label == "daemon tasks"
    assert surfaces["mcp_mcp_plus_plus"].label == "MCP/MCP++"
    assert surfaces["swissknife_orb"].label == "SwissKnife ORB"
    assert surfaces["swissknife_orb"].metadata["virtual_ui_plane"] == (
        "swissknife.virtual_desktop"
    )
    assert surfaces["swissknife_orb"].metadata["orb_router"] == (
        "swissknife/src/services/mcp-orb-capability-router.ts"
    )
    assert surfaces["swissknife_orb"].metadata["display_descriptor"] == (
        "spec/meta_glasses_display_widget_orb_interface.json"
    )
    assert surfaces["hallucinate_app"].label == "Hallucinate App"
    assert surfaces["mobile_glasses"].label == "mobile/glasses"
