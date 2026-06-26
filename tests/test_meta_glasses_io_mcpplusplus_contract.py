"""Contract guards for the Meta glasses I/O MCP++ conformance artifacts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JEST_CONFORMANCE = (
    ROOT
    / "swissknife"
    / "test"
    / "mcp-plus-plus"
    / "meta-glasses-io-conformance.test.ts"
)
DOC = ROOT / "docs" / "meta-glasses-io-conformance.md"

REQUIRED_CAPABILITIES = {
    "camera.photo_capture",
    "microphone.input",
    "neural_band.input",
    "captouch.input",
    "motion.orientation",
    "phone_gps.context",
    "display.output",
}

REQUIRED_CONFORMANCE_TERMS = {
    "stable content CIDs",
    "libp2p peer/session identifiers",
    "MCP++ tool/event receipts",
    "explicit policy decisions",
    "privacy redaction metadata",
    "bridge route state",
    "control-plane route decisions",
    "app binding IDs",
    "fallback behavior",
    "Bluetooth/Wi-Fi envelope metadata",
    "malformed envelopes",
    "unauthorized control-plane handoffs",
}


def test_jest_conformance_suite_covers_required_modalities_and_failure_paths() -> None:
    source = JEST_CONFORMANCE.read_text(encoding="utf-8")

    for capability in REQUIRED_CAPABILITIES:
        assert capability in source
    for token in [
        "validateMetaGlassesIOBridgeEnvelope",
        "META_GLASSES_IO_TRANSPORT_ERROR_CODES.APP_LAYER_BOUNDARY",
        "META_GLASSES_IO_TRANSPORT_ERROR_CODES.CONTENT_CIDS",
        "META_GLASSES_IO_TRANSPORT_ERROR_CODES.RECEIPTS",
        "policy-deny-unauthorized-display-handoff",
        "raw_transport_is_ipfs_libp2p_or_mcp",
        "libp2p_peer_id",
        "libp2p_session_id",
        "mcp_tool_receipt_id",
        "mcp_event_receipt_id",
        "inline_payload_allowed",
        "raw_payload_forwarded",
        "fallback",
    ]:
        assert token in source


def test_conformance_doc_names_acceptance_invariants_and_validation_commands() -> None:
    doc = DOC.read_text(encoding="utf-8")

    assert "MGW-371" in doc
    for term in REQUIRED_CONFORMANCE_TERMS:
        assert term in doc
    assert (
        "PYTHONPATH=./src pytest tests/test_meta_glasses_io_mcpplusplus_contract.py"
        in doc
    )
    assert (
        "cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-conformance.test.ts"
        in doc
    )


def test_conformance_artifacts_are_scoped_to_test_and_doc_outputs() -> None:
    assert JEST_CONFORMANCE.exists()
    assert DOC.exists()
    assert JEST_CONFORMANCE.name == "meta-glasses-io-conformance.test.ts"
    assert DOC.name == "meta-glasses-io-conformance.md"
