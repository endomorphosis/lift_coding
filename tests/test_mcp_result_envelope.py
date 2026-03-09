"""Tests for MCP result envelope normalization."""

from handsfree.mcp import build_result_envelope, build_result_envelope_from_invocation, envelope_to_trace
from handsfree.mcp.models import MCPToolInvocationResult


def test_build_result_envelope_preserves_core_metadata():
    envelope = build_result_envelope(
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        capability_id="ipfs_pin",
        execution_mode="direct_import",
        status="completed",
        tool_name="ipfs_kit.pin",
        spoken_text="Pinned bafy123.",
        structured_output={"cid": "bafy123", "message": "Pinned bafy123."},
    )

    trace = envelope_to_trace(envelope)

    assert envelope.summary == "Pinned bafy123."
    assert envelope.artifact_refs.result_cid == "bafy123"
    assert trace["mcp_result_preview"] == "Pinned bafy123."
    assert trace["mcp_result_cid"] == "bafy123"
    assert trace["mcp_result_envelope"]["execution_mode"] == "direct_import"


def test_build_result_envelope_from_invocation_normalizes_success_output():
    invocation = MCPToolInvocationResult(
        request_id="req-1",
        run_id=None,
        status="completed",
        tool_name="tools_dispatch",
        output={
            "status": "success",
            "message": "Expanded legal query",
            "result_cid": "bafy-expanded",
        },
        content=[],
        raw_response={},
    )

    envelope = build_result_envelope_from_invocation(
        provider_name="ipfs_datasets_mcp",
        server_family="ipfs_datasets",
        capability_id="dataset_discovery",
        execution_mode="mcp_remote",
        invocation=invocation,
    )

    assert envelope.status == "completed"
    assert envelope.spoken_text == "Expanded legal query"
    assert envelope.trace.request_id == "req-1"
    assert envelope.artifact_refs.result_cid == "bafy-expanded"
