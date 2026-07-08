"""Hallucinate App/mobile interoperability regression tests for MGW-579."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.hallucinate_app_mobile_interop import (  # noqa: E402
    EVENT_NAME,
    GOAL_ID,
    INTERFACE_CONTRACT,
    REQUIRED_CONTENT_BROWSER_OPERATIONS,
    REQUIRED_MOBILE_WIDGET_ACTIONS,
    REQUIRED_TIME_SERIES_TABLES,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_handoff,
    discover_hallucinate_app_mobile_contract,
)

HALLUCINATE_APP_ROOT = REPO_ROOT / "hallucinate_app"
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
const classExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  classExports.push(name);
  return `class ${name} `;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
source = `${source}\n${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  const value = context.exports[name];
  selected[name] = typeof value === 'function'
    ? value({ query: 'gpu benchmark', filter: { mimetype: 'application/json' }, resultCount: 2 })
    : value;
}
process.stdout.write(JSON.stringify(selected));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), json.dumps(export_names)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def read_fixture_json() -> dict:
    html = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<script[^>]+id="hallucinate-app-mobile-interop-fixture"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, "missing hallucinate-app-mobile-interop-fixture"
    return json.loads(match.group(1))


def test_expected_hallucinate_app_mobile_descriptor_assets_exist_on_disk() -> None:
    expected_paths = [
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_hallucinate_app_mobile_contract_finds_required_terms() -> None:
    contract = discover_hallucinate_app_mobile_contract(HALLUCINATE_APP_ROOT)

    assert contract.search_interface_path.endswith(
        "hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    assert contract.test_interface_path.endswith("hallucinate_app/node/views/test_interface.html")
    assert set(REQUIRED_CONTENT_BROWSER_OPERATIONS).issubset(
        set(contract.content_browser_operations)
    )
    assert set(REQUIRED_MOBILE_WIDGET_ACTIONS).issubset(set(contract.mobile_widget_actions))
    assert "hallucinate-app-mobile-interop-fixture" in contract.html_fixture_ids
    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(contract.time_series_tables))
    assert "create_performance_tables" in contract.benchmark_schema_functions
    assert "create_hallucinate_app_mobile_interop_tables" in (
        contract.benchmark_schema_functions
    )


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    try:
        discover_hallucinate_app_mobile_contract(tmp_path / "missing")
    except HallucinateAppMobileInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_handoff_is_deterministic() -> None:
    payload = {
        "query": "gpu benchmark",
        "filter": {"mimetype": "application/json"},
        "result_count": 3,
    }
    first = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT, payload=payload)
    second = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT, payload=payload)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.goal_id == GOAL_ID
    assert first.source_repository == "hallucinate_app"
    assert first.target_repository == "mobile"
    assert first.event_name == EVENT_NAME
    assert first.route == "hallucinate-app-content-browser-to-mobile-widget"
    assert first.endpoint_path == "/v1/hallucinate-app/content-browser/search"
    assert first.method == "POST"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_MOBILE_WIDGET_ACTIONS).issubset(
        set(first.required_mobile_widget_actions)
    )
    assert "hallucinate_app_mobile_interop_events" in first.time_series_tables


def test_search_interface_exports_hallucinate_app_mobile_handoff_descriptor() -> None:
    assert_module_is_valid_esm(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_CONTENT_BROWSER_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_WIDGET_ACTIONS",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "buildHallucinateAppMobileInteropHandoff",
        ],
    )

    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    handoff = exports["buildHallucinateAppMobileInteropHandoff"]

    assert set(exports["HALLUCINATE_APP_CONTENT_BROWSER_OPERATIONS"]) == set(
        REQUIRED_CONTENT_BROWSER_OPERATIONS
    )
    assert set(exports["HALLUCINATE_APP_MOBILE_WIDGET_ACTIONS"]) == set(
        REQUIRED_MOBILE_WIDGET_ACTIONS
    )
    assert descriptor["interface"]["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert descriptor["interface"]["metadata"]["goal_id"] == GOAL_ID
    assert descriptor["runtime_handoff"]["event_name"] == EVENT_NAME
    assert descriptor["runtime_handoff"]["route"] == (
        "hallucinate-app-content-browser-to-mobile-widget"
    )
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert handoff["interface_contract"] == INTERFACE_CONTRACT
    assert handoff["action_id"] == "mobile_render_search_results_widget"


def test_hallucinate_app_test_interface_contains_mobile_fixture() -> None:
    fixture = read_fixture_json()

    assert fixture["task_id"] == "MGW-579"
    assert fixture["goal_id"] == GOAL_ID
    assert fixture["interface_contract"] == INTERFACE_CONTRACT
    assert fixture["event_name"] == EVENT_NAME
    assert set(fixture["content_browser_operations"]) == set(
        REQUIRED_CONTENT_BROWSER_OPERATIONS
    )
    assert set(fixture["mobile_widget_actions"]) == set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    assert fixture["evidence"] == "objective validation repair"


def test_duckdb_schema_records_hallucinate_app_mobile_interop_events() -> None:
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    for content in (schema, script):
        assert "hallucinate_app_mobile_interop_events" in content
        assert INTERFACE_CONTRACT in content
        assert GOAL_ID in content
        assert EVENT_NAME in content
        assert "objective validation repair" in content
    assert "create_hallucinate_app_mobile_interop_tables" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_TABLES" in script


def test_mobile_descriptor_exports_matching_hallucinate_app_mobile_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_SEARCH_WIDGET_OPERATIONS",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | set(REQUIRED_MOBILE_WIDGET_ACTIONS)
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["HALLUCINATE_APP_MOBILE_SEARCH_WIDGET_OPERATIONS"]) == set(
        REQUIRED_MOBILE_WIDGET_ACTIONS
    )
    assert descriptor["schema_refs"] == {
        "search_interface": (
            "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
        ),
        "test_interface_fixture": (
            "hallucinate_app/hallucinate_app/node/views/test_interface.html"
        ),
        "time_series_schema": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
        ),
        "benchmark_schema_script": (
            "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
        ),
        "mobile_orb_bridge": "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["event_name"] == EVENT_NAME
    assert "hallucinate_app_mobile_interop_events" in (
        descriptor["runtime_handoff"]["time_series_tables"]
    )
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "MGW-579",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app_mobile_interop_events",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
