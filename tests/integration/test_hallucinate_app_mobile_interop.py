"""VAIOS-G707 Hallucinate App <-> mobile interoperability evidence."""

from __future__ import annotations

import py_compile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOBILE_DESCRIPTORS = ROOT / "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_BRIDGE = ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js"
SEARCH_INTERFACE = (
    ROOT
    / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE = ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
TIME_SERIES_SCHEMA = (
    ROOT
    / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
CREATE_SCHEMA = (
    ROOT
    / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
DOC = ROOT / "docs/integration/hallucinate_app-mobile.md"
HEAP = ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
DISCOVERY = (
    ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-671-objective-validation-repair.md"
)


def read(path: Path) -> str:
    assert path.exists(), f"Expected evidence file is missing: {path}"
    return path.read_text(encoding="utf-8")


def test_mobile_exports_and_advertises_hallucinate_app_interop_descriptor() -> None:
    descriptors = read(MOBILE_DESCRIPTORS)
    bridge = read(MOBILE_BRIDGE)

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in descriptors
    assert "handsfree.interop.hallucinate_app_mobile" in descriptors
    assert "dispatch_content_search" in descriptors
    assert "hallucinate_app/control-surface-mediation" in descriptors
    assert "mobile/meta-glasses-orb-bridge" in descriptors

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in bridge
    assert "descriptorRef(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in bridge
    assert bridge.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1
    assert "this.operationReceipts = [];" in bridge
    assert "const operationReceipts = [...this.operationReceipts];" in bridge


def test_hallucinate_search_interface_builds_mobile_handoff_envelope() -> None:
    source = read(SEARCH_INTERFACE)

    assert "HALLUCINATE_APP_MOBILE_SEARCH_DESCRIPTOR" in source
    assert "schema: 'hallucinate_app_mobile_content_search_handoff_v1'" in source
    assert "objective_id: 'VAIOS-G707'" in source
    assert "handsfree.interop.hallucinate_app_mobile/handoff@0.1.0" in source
    assert "buildMobileHandoffSearchRequest" in source
    assert "hallucinate_app:mobile-handoff-search" in source
    assert "handoff.ipfs_cids" in source
    assert "libp2p_peer_id" in source
    assert "mediation_receipt" in source


def test_hallucinate_test_interface_contains_mobile_orb_runner() -> None:
    html = read(TEST_INTERFACE)

    assert 'data-module="mobile-orb"' in html
    assert 'id="mobile-orb-section"' in html
    assert 'id="btnTestMobileOrb"' in html
    assert 'id="mobileOrbConfig"' in html
    assert "VAIOS-G707" in html
    assert "handsfree.interop.hallucinate_app_mobile/handoff@0.1.0" in html
    assert "dispatch_content_search" in html


def test_duckdb_schema_records_hallucinate_app_mobile_handoffs() -> None:
    schema = read(TIME_SERIES_SCHEMA)
    creator = read(CREATE_SCHEMA)

    for source in (schema, creator):
        assert "hallucinate_app_mobile_handoff_events" in source
        assert "VAIOS-G707" in source
        assert "interface_contract" in source
        assert "edge_session_id" in source
        assert "correlation_id" in source
        assert "ipfs_cids" in source
        assert "libp2p_peer_id" in source
        assert "mediation_receipt" in source

    py_compile.compile(str(CREATE_SCHEMA), doraise=True)


def test_contract_doc_discovery_and_heap_capture_validation_repair() -> None:
    doc = read(DOC)
    discovery = read(DISCOVERY)
    heap = read(HEAP)

    for source in (doc, discovery):
        assert "VAIOS-G707" in source
        assert "hallucinate_app" in source
        assert "mobile" in source
        assert "interface contract" in source.lower()
        assert "runtime handoff" in source.lower()

    goal_block = re.search(
        r"## VAIOS-G707 Interoperate hallucinate_app with mobile(?P<body>.*?)(?:\n## |\Z)",
        heap,
        flags=re.S,
    )
    assert goal_block, "VAIOS-G707 heap entry is missing"
    body = goal_block.group("body")
    assert "tests/integration/test_hallucinate_app_mobile_interop.py" in body
    assert "docs/integration/hallucinate_app-mobile.md" in body
    assert "objective validation repair" in body
    assert "2026-07-08-vai-671-objective-validation-repair.md" in body
