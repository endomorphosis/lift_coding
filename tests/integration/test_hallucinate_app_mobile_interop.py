"""VAIOS-G707 objective validation repair for hallucinate_app <-> mobile.

The test is intentionally hardware-free: it proves the two surfaces share an
importable/textual interface descriptor, handoff event, mobile route, test
fixture, and DuckDB persistence schema without requiring Electron or a phone.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACT = "interface contract hallucinate_app mobile"
OBJECTIVE_ID = "VAIOS-G707"
DESCRIPTOR_NAME = "hallucinate_app_mobile_content_browser"
DESCRIPTOR_NAMESPACE = "handsfree.hallucinate_app.mobile"
DESCRIPTOR_VERSION = "0.1.0"
HANDOFF_EVENT = "hallucinate-app:mobile-interop-handoff"
MOBILE_ROUTE = "mobile://hallucinate_app/content-browser/search"


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_hallucinate_search_interface_exports_mobile_handoff_contract():
    source = read(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/"
        "search_interface.js"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "buildHallucinateAppMobileSearchHandoff" in source
    assert CONTRACT in source
    assert OBJECTIVE_ID in source
    assert DESCRIPTOR_NAME in source
    assert DESCRIPTOR_NAMESPACE in source
    assert HANDOFF_EVENT in source
    assert MOBILE_ROUTE in source
    assert "this.emit('mobile-interop-handoff', mobileHandoff)" in source
    assert re.search(r"eventBus\.emit\(\s*HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR\.event", source)


def test_mobile_descriptor_matches_hallucinate_descriptor():
    mobile_descriptor = read("mobile/src/orb/metaGlassesOrbDescriptors.js")
    bridge = read("mobile/src/orb/metaGlassesMobileOrbBridge.js")

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in mobile_descriptor
    assert "buildHallucinateAppMobileInteropReceipt" in mobile_descriptor
    for term in [
        CONTRACT,
        OBJECTIVE_ID,
        DESCRIPTOR_NAME,
        DESCRIPTOR_NAMESPACE,
        DESCRIPTOR_VERSION,
        "ingest_content_search",
        "apply_content_filter",
        "open_module_test_interface",
        "record_benchmark_timeseries_sample",
        MOBILE_ROUTE,
    ]:
        assert term in mobile_descriptor

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in bridge
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in bridge
    assert "descriptorRef(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in bridge


def test_test_interface_html_carries_machine_readable_mobile_contract():
    html = read("hallucinate_app/hallucinate_app/node/views/test_interface.html")
    match = re.search(
        r'<script type="application/json" id="hallucinate-app-mobile-interop-contract">\s*(\{.*?\})\s*</script>',
        html,
        re.DOTALL,
    )
    assert match, "test_interface.html must expose the mobile interop contract JSON"

    payload = json.loads(match.group(1))
    assert payload["contract"] == CONTRACT
    assert payload["objective_id"] == OBJECTIVE_ID
    assert payload["descriptor"]["name"] == DESCRIPTOR_NAME
    assert payload["descriptor"]["namespace"] == DESCRIPTOR_NAMESPACE
    assert payload["descriptor"]["version"] == DESCRIPTOR_VERSION
    assert payload["mobile_route"] == MOBILE_ROUTE
    assert payload["dashboard_event"] == HANDOFF_EVENT
    assert "buildModuleTestHandoff" in html


def test_duckdb_schema_records_hallucinate_mobile_interop_timeseries():
    schema = read(
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/"
        "time_series_schema.sql"
    )
    for term in [
        "hallucinate_app_mobile_interop_events",
        "hallucinate_app_mobile_benchmark_samples",
        "hallucinate_app_mobile_interop_timeseries",
        CONTRACT,
        OBJECTIVE_ID,
        DESCRIPTOR_NAMESPACE,
        DESCRIPTOR_NAME,
        "idx_hallucinate_app_mobile_interop_contract",
    ]:
        assert term in schema


def test_benchmark_schema_creator_is_importable_and_defines_contract_schema():
    script_path = (
        ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/"
        "create_benchmark_schema.py"
    )
    source = script_path.read_text(encoding="utf-8")
    ast.parse(source)

    for term in [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinate_app_mobile_interop_schema_sql",
        "create_hallucinate_app_mobile_interop_tables",
        CONTRACT,
        OBJECTIVE_ID,
        DESCRIPTOR_NAMESPACE,
        DESCRIPTOR_NAME,
    ]:
        assert term in source


def test_documentation_and_objective_heap_record_validation_repair():
    doc = read("docs/integration/hallucinate_app-mobile.md")
    heap = read("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")
    discovery = read(
        "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-579-objective-validation-repair.md"
    )

    for text in (doc, heap, discovery):
        assert CONTRACT in text
        assert OBJECTIVE_ID in text
        assert "objective validation repair" in text
        assert "tests/integration/test_hallucinate_app_mobile_interop.py" in text

    assert "MGW-579 objective validation repair" in heap
