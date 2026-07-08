"""VAIOS-G707 hallucinate_app <-> mobile interoperability evidence."""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH_INTERFACE = (
    REPO_ROOT
    / "hallucinate_app"
    / "hallucinate_app"
    / "node"
    / "dashboard"
    / "content_browser"
    / "search_interface.js"
)
TEST_INTERFACE = (
    REPO_ROOT
    / "hallucinate_app"
    / "hallucinate_app"
    / "node"
    / "views"
    / "test_interface.html"
)
TIME_SERIES_SCHEMA = (
    REPO_ROOT
    / "hallucinate_app"
    / "ipfs_accelerate_py"
    / "data"
    / "duckdb"
    / "db_schema"
    / "time_series_schema.sql"
)
CREATE_BENCHMARK_SCHEMA = (
    REPO_ROOT
    / "hallucinate_app"
    / "ipfs_accelerate_py"
    / "data"
    / "duckdb"
    / "scripts"
    / "create_benchmark_schema.py"
)
MOBILE_INTEROP = REPO_ROOT / "mobile" / "src" / "utils" / "hallucinateAppMobileInterop.js"
MOBILE_ACTIONS = REPO_ROOT / "mobile" / "src" / "utils" / "agentActions.js"
DOC = REPO_ROOT / "docs" / "integration" / "hallucinate_app-mobile.md"
DISCOVERY = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-07-08-vai-671-objective-validation-repair.md"
)
HEAP = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_python_contract_builds_and_validates_mobile_handoff() -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from handsfree.hallucinate_app_mobile_interop import (
        HALLUCINATE_APP_MOBILE_ACTION_ID,
        HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        build_mobile_search_handoff,
        validate_mobile_search_handoff,
    )

    payload = build_mobile_search_handoff(
        query="cid:QmDemo mobile handoff",
        filters={"mimetype": "text/plain"},
        cid="QmDemo",
        metadata={"objective": "VAIOS-G707"},
    )

    assert payload["contract"] == HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT
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
        "buildHallucinateAppMobileSearchEnvelope",
        "launchMobileSearch",
        "publishMobileHandoff",
        "dispatchMobileAction",
        "hallucinate_app:mobile-search-handoff",
        "content-browser:mobile-search",
        "mobile_hallucinate_app_search",
        "mobile_payload",
        "transport.handoff",
        "mcp_plus_plus_profile",
    ]:
        assert token in source


def test_dashboard_handoff_builder_is_importable_in_node() -> None:
    script = f"""
      import {{ buildHallucinateAppMobileSearchEnvelope }} from {json.dumps(SEARCH_INTERFACE.as_uri())};
      const envelope = buildHallucinateAppMobileSearchEnvelope({{
        query: 'cid:QmDemo mobile',
        filter: {{ mimetype: 'text/plain' }},
        cid: 'QmDemo',
        requestId: 'vaios-g707-node'
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
        "hallucinate-app-mobile-interop-card",
        "hallucinateMobilePayload",
        "hallucinate-app-mobile-handoff",
        "hallucinate-app-mobile-handoff-result",
        "handsfree.hallucinate_app/mobile-search-handoff@0.1.0",
        "mobile_hallucinate_app_search",
        "hallucinate_app:mobile-search-handoff",
    ]:
        assert token in html


def test_duckdb_schema_tracks_mobile_interop_receipts() -> None:
    sql = read(TIME_SERIES_SCHEMA)
    for token in [
        "hallucinate_app_mobile_handoffs",
        "hallucinate_app_mobile_handoff_assertions",
        "hallucinate_app_mobile_interop_status",
        "handsfree.hallucinate_app/mobile-search-handoff@0.1.0",
        "mobile_hallucinate_app_search",
        "mobile_payload JSON",
        "control_plane JSON",
        "receipts JSON",
    ]:
        assert token in sql


def test_create_benchmark_schema_is_valid_python_and_defines_interop_tables(tmp_path: Path) -> None:
    source = read(CREATE_BENCHMARK_SCHEMA)
    ast.parse(source)

    spec = importlib.util.spec_from_file_location("create_benchmark_schema", CREATE_BENCHMARK_SCHEMA)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT == (
        "handsfree.hallucinate_app/mobile-search-handoff@0.1.0"
    )
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


def test_docs_heap_and_discovery_record_objective_validation_repair() -> None:
    doc = read(DOC)
    heap = read(HEAP)
    discovery = read(DISCOVERY)

    for source in [doc, heap, discovery]:
        assert "VAIOS-G707" in source
        assert "hallucinate_app" in source
        assert "mobile" in source
        assert "objective validation repair" in source.lower()

    assert "tests/integration/test_hallucinate_app_mobile_interop.py" in heap
    assert "docs/integration/hallucinate_app-mobile.md" in discovery
