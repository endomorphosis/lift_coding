"""VAIOS-G707 Hallucinate App <-> mobile interoperability evidence."""

from __future__ import annotations

import ast
import importlib.util
import json
import py_compile
import re
import subprocess
from pathlib import Path

import pytest

from handsfree.hallucinate_app_mobile_interop import (
    HALLUCINATE_APP_MOBILE_ACTION_ID,
    HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
    build_mobile_search_handoff,
    validate_mobile_search_handoff,
)


ROOT = Path(__file__).resolve().parents[2]
MOBILE_INTEROP = ROOT / "mobile/src/utils/hallucinateAppMobileInterop.js"
MOBILE_ACTIONS = ROOT / "mobile/src/utils/agentActions.js"
SEARCH_INTERFACE = (
    ROOT
    / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE = ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
TIME_SERIES_SCHEMA = (
    ROOT
    / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
CREATE_BENCHMARK_SCHEMA = (
    ROOT
    / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
DOC = ROOT / "docs/integration/hallucinate_app-mobile.md"
HEAP = ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
DISCOVERY = (
    ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-671-objective-validation-repair.md"
)
RETRY_DISCOVERY = (
    ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-673-vai-671-retry-budget.md"
)


def read(path: Path) -> str:
    assert path.exists(), f"Expected evidence file is missing: {path}"
    return path.read_text(encoding="utf-8")


def test_python_contract_builds_valid_runtime_handoff() -> None:
    payload = build_mobile_search_handoff(
        query="cid:QmDemo mobile",
        filter={"mimetype": "text/plain"},
        cid="QmDemo",
        request_id="vaios-g707-python",
        edge_session_id="edge-session-1",
        libp2p_peer_id="12D3KooWMobile",
        timestamp="2026-07-08T00:00:00Z",
    )

    assert payload["action_id"] == HALLUCINATE_APP_MOBILE_ACTION_ID
    assert payload["event_type"] == "transport.handoff"
    assert payload["profile"] == "swissknife.mcp++/event-envelope@0.1.0"
    assert payload["control_plane"]["route"] == "hallucinate_app.mobile.search_handoff"
    assert payload["mobile_payload"]["target_surface"] == "mobile.results"
    assert payload["handoff"]["ipfs_cids"] == ["QmDemo"]
    assert payload["receipt_cid"].startswith("sha256:hallucinate-app-mobile:")
    assert validate_mobile_search_handoff(payload)["type"] == HALLUCINATE_APP_MOBILE_ACTION_ID


def test_dashboard_search_interface_exports_runtime_handoff_builder() -> None:
    source = read(SEARCH_INTERFACE)
    for token in [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "HALLUCINATE_APP_MOBILE_SEARCH_DESCRIPTOR",
        "buildMobileHandoffSearchRequest",
        "buildHallucinateAppMobileSearchEnvelope",
        "launchMobileSearch",
        "publishMobileHandoff",
        "dispatchMobileAction",
        "hallucinate_app:mobile-handoff-search",
        "content-browser:mobile-search",
        "mobile_hallucinate_app_search",
        "mobile_payload",
        "transport.handoff",
        "mcp_plus_plus_profile",
        "libp2p_peer_id",
        "mediation_receipt",
    ]:
        assert token in source


def test_dashboard_handoff_builder_is_importable_in_node() -> None:
    script = f"""
      import {{ buildHallucinateAppMobileSearchEnvelope }} from {json.dumps(SEARCH_INTERFACE.as_uri())};
      const envelope = buildHallucinateAppMobileSearchEnvelope({{
        query: 'cid:QmDemo mobile',
        filter: {{ mimetype: 'text/plain' }},
        cid: 'QmDemo',
        requestId: 'vaios-g707-node',
        edgeSessionId: 'edge-session-node'
      }});
      console.log(JSON.stringify(envelope));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        text=True,
        capture_output=True,
    )
    envelope = json.loads(result.stdout)
    assert envelope["request_id"] == "vaios-g707-node"
    assert envelope["mobile_payload"]["type"] == "mobile_hallucinate_app_search"
    assert envelope["handoff"]["ipfs_cids"] == ["QmDemo"]
    assert envelope["handoff"]["edge_session_id"] == "edge-session-node"


def test_mobile_utility_and_action_dispatcher_accept_hallucinate_app_action() -> None:
    utility = read(MOBILE_INTEROP)
    actions = read(MOBILE_ACTIONS)

    for token in [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "normalizeHallucinateAppMobilePayload",
        "buildHallucinateAppMobileSearchAction",
        "mobile_hallucinate_app_search",
        "source_surface",
        "target_surface",
    ]:
        assert token in utility

    assert "isHallucinateAppMobileActionId" in actions
    assert "normalizeHallucinateAppMobilePayload" in actions
    assert "navigate('Results', { hallucinateAppSearch: payload })" in actions
    assert "hallucinate_app_mobile_search" in actions


def test_test_interface_exposes_operator_mobile_handoff_panel() -> None:
    html = read(TEST_INTERFACE)
    for token in [
        'data-module="mobile-orb"',
        'id="mobile-orb-section"',
        'id="btnTestMobileOrb"',
        'id="mobileOrbConfig"',
        "hallucinate-app-mobile-interop-card",
        "hallucinateMobilePayload",
        "hallucinate-app-mobile-handoff",
        "hallucinate-app-mobile-handoff-result",
        HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        "mobile_hallucinate_app_search",
        "dispatch_content_search",
        "VAIOS-G707",
    ]:
        assert token in html


def test_duckdb_schema_tracks_mobile_interop_receipts() -> None:
    sql = read(TIME_SERIES_SCHEMA)
    for token in [
        "hallucinate_app_mobile_handoffs",
        "hallucinate_app_mobile_handoff_assertions",
        "hallucinate_app_mobile_interop_status",
        HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        "mobile_hallucinate_app_search",
        "mobile_payload JSON",
        "control_plane JSON",
        "receipts JSON",
        "edge_session_id",
        "correlation_id",
        "ipfs_cids",
        "libp2p_peer_id",
        "mediation_receipt",
    ]:
        assert token in sql


def test_create_benchmark_schema_is_valid_python_and_defines_interop_tables(tmp_path: Path) -> None:
    source = read(CREATE_BENCHMARK_SCHEMA)
    ast.parse(source)
    py_compile.compile(str(CREATE_BENCHMARK_SCHEMA), doraise=True)

    spec = importlib.util.spec_from_file_location(
        "create_benchmark_schema", CREATE_BENCHMARK_SCHEMA
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT == HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT
    assert hasattr(module, "create_hallucinate_app_mobile_tables")
    assert "hallucinate_app_mobile_handoffs" in source
    assert "hallucinate_app_mobile_interop_status" in source

    pytest.importorskip("duckdb")
    conn = module.connect_to_db(tmp_path / "benchmark.duckdb")
    try:
        module.create_schema(conn, force=True)
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        assert "hallucinate_app_mobile_handoffs" in tables
        assert "hallucinate_app_mobile_handoff_assertions" in tables
        assert "hallucinate_app_mobile_interop_status" in tables
    finally:
        conn.close()


def test_docs_heap_and_discovery_record_retry_budget_repair() -> None:
    doc = read(DOC)
    heap = read(HEAP)
    discovery = read(DISCOVERY)
    retry_discovery = read(RETRY_DISCOVERY)

    for source in [doc, heap, discovery]:
        assert "VAIOS-G707" in source
        assert "hallucinate_app" in source
        assert "mobile" in source
        assert "interface contract" in source.lower()
        assert "runtime handoff" in source.lower()
        assert "objective validation repair" in source.lower()

    assert "Retry-budget" in discovery
    assert "VAI-673" in discovery
    assert "Observed consecutive validation failures: 3" in retry_discovery
    assert "tests/integration/test_hallucinate_app_mobile_interop.py" in heap
    assert "docs/integration/hallucinate_app-mobile.md" in discovery

    goal_block = re.search(
        r"## VAIOS-G707 Interoperate hallucinate_app with mobile(?P<body>.*?)(?:\n## |\Z)",
        heap,
        flags=re.S,
    )
    assert goal_block, "VAIOS-G707 heap entry is missing"
    body = goal_block.group("body")
    assert "VAI-673 retry-budget repair" in body
    assert "2026-07-08-vai-671-objective-validation-repair.md" in body
