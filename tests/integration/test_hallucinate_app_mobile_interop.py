"""Integration proof for hallucinate_app <-> mobile interoperability.

This is the non-skipped validation gate for VAIOS-G707 and the MGW-579
retry-budget repair. It checks importable/textual contracts without requiring
Electron, React Native, or physical glasses.
"""

from __future__ import annotations

import importlib.util
import json
import py_compile
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

SEARCH_INTERFACE = ROOT / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
TEST_INTERFACE_HTML = ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
MOBILE_DESCRIPTORS = ROOT / "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_BRIDGE = ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js"
MOBILE_RUNTIME = ROOT / "mobile/src/orb/metaGlassesMobileOrbRuntime.js"
TIME_SERIES_SCHEMA = ROOT / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
CREATE_SCHEMA_SCRIPT = ROOT / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
INTEGRATION_DOC = ROOT / "docs/integration/hallucinate_app-mobile.md"
OBJECTIVE_HEAP = ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
REPAIR_EVIDENCE = ROOT / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md"
RETRY_BUDGET_EVIDENCE = ROOT / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-582-mgw-579-retry-budget.md"

CONTRACT = "interface contract hallucinate_app mobile"
EVENT = "hallucinate-app:mobile-interop-handoff"
MOBILE_INTERFACE_KEY = "handsfree.meta_glasses.mobile.hallucinate_app_mobile_interop@0.1.0"
INTEROP_TABLE = "hallucinate_app_mobile_interop_events"
RECEIPT_TABLE = "hallucinate_mobile_handoff_receipts"
CONTROL_SURFACE_REF = "control_surface_contract:hallucinate-app:remote-client"


def read(path: Path) -> str:
    assert path.exists(), f"missing expected output: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def load_schema_module():
    py_compile.compile(str(CREATE_SCHEMA_SCRIPT), doraise=True)
    spec = importlib.util.spec_from_file_location("create_benchmark_schema", CREATE_SCHEMA_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hallucinate_app_search_interface_emits_mobile_handoff_contract():
    source = read(SEARCH_INTERFACE)

    for term in [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "buildHallucinateAppMobileSearchHandoff",
        "buildMobileSearchHandoff",
        "recordMobileInteropHandoff",
        CONTRACT,
        EVENT,
        MOBILE_INTERFACE_KEY,
        INTEROP_TABLE,
        "mobile-interop-handoff",
    ]:
        assert term in source

    assert "this._emitMobileInteropHandoff('search')" in source
    assert "this._emitMobileInteropHandoff('filter')" in source
    assert "this._emitMobileInteropHandoff('clear')" in source
    assert "this.eventBus.emit(HALLUCINATE_APP_MOBILE_INTEROP_EVENT, payload)" in source


def test_mobile_orb_advertises_matching_hallucinate_app_descriptor():
    descriptors = read(MOBILE_DESCRIPTORS)
    bridge = read(MOBILE_BRIDGE)
    runtime = read(MOBILE_RUNTIME)

    for text in (descriptors, bridge, runtime):
        assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in text

    for term in [
        "export const HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "export const HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS",
        CONTRACT,
        EVENT,
        INTEROP_TABLE,
        "accept_handoff",
        "acknowledge_handoff",
    ]:
        assert term in descriptors

    assert "descriptorRef(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE, this.localInterfaceCids[2])" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in runtime
    assert re.search(r"^const MOBILE_ORB_DIAGNOSTICS_CONTRACT", bridge, re.MULTILINE) is None
    assert bridge.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_dashboard_fixture_is_machine_readable_and_matches_contract():
    html = read(TEST_INTERFACE_HTML)
    match = re.search(
        r'<script[^>]+id="hallucinate-app-mobile-interop-fixture"[^>]*>\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    assert match, "missing Hallucinate App mobile interop JSON fixture"

    fixture = json.loads(match.group(1))
    assert fixture["contract"] == CONTRACT
    assert fixture["event"] == EVENT
    assert fixture["descriptor"] == "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"
    assert fixture["mobileInterface"] == MOBILE_INTERFACE_KEY
    assert fixture["route"] == {
        "from": "hallucinate_app",
        "to": "mobile",
        "transport": "mobile_orb_bridge",
        "target_surface": "meta_glasses_display",
    }
    assert fixture["persistence"]["duckdbTable"] == INTEROP_TABLE
    assert fixture["persistence"]["receiptTable"] == RECEIPT_TABLE
    assert fixture["samplePayload"]["action"] == "search"
    assert "window.HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT" in html
    assert "buildModuleTestHandoff" in html


def test_duckdb_schema_and_creator_persist_mobile_interop_events(tmp_path):
    schema_sql = read(TIME_SERIES_SCHEMA)
    creator_source = read(CREATE_SCHEMA_SCRIPT)

    for term in [
        f"CREATE TABLE IF NOT EXISTS {INTEROP_TABLE}",
        f"CREATE TABLE IF NOT EXISTS {RECEIPT_TABLE}",
        "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_interop_latest",
        "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_interop_timeseries",
        EVENT,
        CONTRACT,
        MOBILE_INTERFACE_KEY,
        "idx_hallucinate_app_mobile_interop_contract",
    ]:
        assert term in schema_sql

    for term in [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinate_app_mobile_interop_schema_sql",
        "create_hallucinate_app_mobile_interop_tables",
        f"CREATE TABLE IF NOT EXISTS {INTEROP_TABLE}",
        f"CREATE TABLE IF NOT EXISTS {RECEIPT_TABLE}",
    ]:
        assert term in creator_source

    module = load_schema_module()
    assert hasattr(module, "create_hallucinate_app_mobile_interop_tables")
    assert hasattr(module, "create_schema")

    duckdb = pytest.importorskip("duckdb")
    assert duckdb
    conn = module.connect_to_db(tmp_path / "interop.duckdb")
    try:
        module.create_schema(conn, force=True, sample_data=True)
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        assert INTEROP_TABLE in tables
        assert RECEIPT_TABLE in tables
        assert "integration_test_results" in tables
        row = conn.execute(
            f"SELECT contract, event, mobile_operation FROM {INTEROP_TABLE} WHERE event_id = 'event:mgw-579'"
        ).fetchone()
        assert row == (CONTRACT, EVENT, "accept_handoff")
        receipt = conn.execute(
            f"SELECT contract, control_surface_contract_ref, handoff_event FROM {RECEIPT_TABLE}"
        ).fetchone()
        assert receipt == (CONTRACT, CONTROL_SURFACE_REF, EVENT)
    finally:
        conn.close()


def test_docs_heap_discovery_and_retry_evidence_record_validation_repair():
    doc = read(INTEGRATION_DOC)
    heap = read(OBJECTIVE_HEAP)
    repair = read(REPAIR_EVIDENCE)
    retry = read(RETRY_BUDGET_EVIDENCE)

    for text in (doc, heap, repair):
        assert "VAIOS-G707" in text
        assert "MGW-579" in text
        assert CONTRACT in text
        assert EVENT in text
        assert INTEROP_TABLE in text
        assert "tests/integration/test_hallucinate_app_mobile_interop.py" in text

    assert "objective validation repair" in heap
    assert "No smaller child goals are needed" in heap
    assert "MGW-582" in repair
    assert "python -m pytest tests/integration -q" in retry
