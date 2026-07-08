"""Integration proof for hallucinate_app <-> mobile interoperability.

This covers VAIOS-G707 / MGW-579 objective validation repair without requiring
Electron, React Native, or DuckDB to be present in the test environment.
"""

from __future__ import annotations

import importlib.util
import json
import py_compile
import re
from pathlib import Path


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

CONTRACT = "interface contract hallucinate_app mobile"
EVENT = "hallucinate-app:mobile-interop-handoff"
MOBILE_INTERFACE_KEY = "handsfree.meta_glasses.mobile.hallucinate_app_mobile_interop@0.1.0"
INTEROP_TABLE = "hallucinate_app_mobile_interop_events"


def read(path: Path) -> str:
    assert path.exists(), f"missing expected output: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_hallucinate_app_search_interface_emits_mobile_handoff_contract():
    source = read(SEARCH_INTERFACE)

    assert "export const HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "export function buildMobileInteropHandoff" in source
    assert CONTRACT in source
    assert EVENT in source
    assert MOBILE_INTERFACE_KEY in source
    assert INTEROP_TABLE in source

    assert "this._emitMobileInteropHandoff('search')" in source
    assert "this._emitMobileInteropHandoff('filter')" in source
    assert "this._emitMobileInteropHandoff('clear')" in source
    assert "this.eventBus.emit(HALLUCINATE_APP_MOBILE_INTEROP_EVENT, payload)" in source
    assert "recordMobileInteropHandoff" in source


def test_mobile_orb_advertises_matching_hallucinate_app_descriptor():
    descriptors = read(MOBILE_DESCRIPTORS)
    bridge = read(MOBILE_BRIDGE)
    runtime = read(MOBILE_RUNTIME)

    assert "export const HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in descriptors
    assert "export const HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS" in descriptors
    assert CONTRACT in descriptors
    assert EVENT in descriptors
    assert INTEROP_TABLE in descriptors
    assert "accept_handoff" in descriptors
    assert "acknowledge_handoff" in descriptors

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in bridge
    assert "descriptorRef(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE, this.localInterfaceCids[2])" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in runtime

    assert re.search(r"^const MOBILE_ORB_DIAGNOSTICS_CONTRACT", bridge, re.MULTILINE) is None
    assert bridge.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_dashboard_fixture_is_machine_readable_and_matches_contract():
    html = read(TEST_INTERFACE_HTML)
    match = re.search(
        r'<script type="application/json" id="hallucinate-app-mobile-interop-fixture">\s*(.*?)\s*</script>',
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
    assert fixture["samplePayload"]["action"] == "search"


def test_duckdb_schema_and_creator_persist_mobile_interop_events():
    schema_sql = read(TIME_SERIES_SCHEMA)
    creator_source = read(CREATE_SCHEMA_SCRIPT)

    assert f"CREATE TABLE IF NOT EXISTS {INTEROP_TABLE}" in schema_sql
    assert "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_interop_latest" in schema_sql
    assert EVENT in schema_sql
    assert CONTRACT in schema_sql
    assert MOBILE_INTERFACE_KEY in schema_sql

    assert "def create_hallucinate_app_mobile_interop_tables" in creator_source
    assert f"CREATE TABLE IF NOT EXISTS {INTEROP_TABLE}" in creator_source
    assert "def create_schema" in creator_source
    assert "create_hallucinate_app_mobile_interop_tables(conn, False)" in creator_source

    py_compile.compile(str(CREATE_SCHEMA_SCRIPT), doraise=True)
    spec = importlib.util.spec_from_file_location("create_benchmark_schema", CREATE_SCHEMA_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "create_hallucinate_app_mobile_interop_tables")
    assert hasattr(module, "create_schema")


def test_docs_heap_and_discovery_record_objective_validation_repair():
    doc = read(INTEGRATION_DOC)
    heap = read(OBJECTIVE_HEAP)
    repair = read(REPAIR_EVIDENCE)

    for text in (doc, heap, repair):
        assert "VAIOS-G707" in text
        assert "MGW-579" in text
        assert CONTRACT in text
        assert EVENT in text
        assert INTEROP_TABLE in text

    assert "objective validation repair" in heap
    assert "No smaller child goals are needed" in heap
    assert "tests/integration/test_hallucinate_app_mobile_interop.py" in repair
