"""Hallucinate App/mobile interoperability regression tests for VAI-674."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.hallucinate_app_mobile_interop import (  # noqa: E402
    CANONICAL_EVENT_NAME,
    GOAL_ID,
    INTERFACE_CONTRACT,
    REQUIRED_MOBILE_ORB_ROUTES,
    REQUIRED_RECEIPT_ARTIFACTS,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_handoff,
    discover_hallucinate_app_mobile_contract,
)

HALLUCINATE_APP_ROOT = REPO_ROOT / "hallucinate_app"
MOBILE_ROOT = REPO_ROOT / "mobile"

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
DISPLAY_WIDGET_OPERATIONS = {
    "render_widget",
    "update_widget",
    "clear_widget",
    "focus_next",
    "focus_previous",
    "activate",
    "reset_session",
    "play_video",
    "subscribe_updates",
}


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, 'class $1');
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  selected[name] = context.exports[name];
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


def call_search_handoff_builder() -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, 'class $1');
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('cid:sample', {
  filter: { mimetype: 'application/json' },
  correlation_id: 'test-correlation',
  issued_at: '2026-07-08T00:00:00Z',
});
process.stdout.write(JSON.stringify(handoff));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(
                REPO_ROOT
                / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
            ),
        ],
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


def test_discover_hallucinate_app_mobile_contract_finds_all_artifacts() -> None:
    contract = discover_hallucinate_app_mobile_contract(
        HALLUCINATE_APP_ROOT,
        MOBILE_ROOT,
    )

    assert contract.routes == REQUIRED_MOBILE_ORB_ROUTES
    assert contract.receipt_artifacts == REQUIRED_RECEIPT_ARTIFACTS
    assert "hallucinate_app_mobile_interop_receipts" in contract.persistence_tables
    assert "hallucinate_app_mobile_interop_events" in contract.persistence_tables
    assert CANONICAL_EVENT_NAME in contract.event_names
    assert contract.search_interface_path.endswith(
        "hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    assert contract.test_interface_path.endswith("hallucinate_app/node/views/test_interface.html")
    assert contract.mobile_descriptor_path.endswith("src/orb/metaGlassesOrbDescriptors.js")
    assert contract.mobile_bridge_path.endswith("src/orb/metaGlassesMobileOrbBridge.js")


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    try:
        discover_hallucinate_app_mobile_contract(tmp_path / "missing-ha", MOBILE_ROOT)
    except HallucinateAppMobileInteropError as exc:
        assert "hallucinate_app root not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_handoff_is_deterministic() -> None:
    first = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT, MOBILE_ROOT)
    second = build_hallucinate_app_mobile_handoff(HALLUCINATE_APP_ROOT, MOBILE_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.goal_id == GOAL_ID
    assert first.event_name == CANONICAL_EVENT_NAME
    assert first.source_repository == "hallucinate_app"
    assert first.target_repository == "mobile"
    assert first.route == "/v1/mobile/orb/invoke_service"
    assert first.operation == "invoke_service"
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert first.required_mobile_orb_routes == REQUIRED_MOBILE_ORB_ROUTES
    assert first.required_receipt_artifacts == REQUIRED_RECEIPT_ARTIFACTS
    assert "hallucinate_app_mobile_interop_events" in first.persistence_tables


def test_hallucinate_app_search_interface_exports_canonical_handoff() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_EVENT",
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    handoff = call_search_handoff_builder()

    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_EVENT"] == CANONICAL_EVENT_NAME
    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["goal_id"] == GOAL_ID
    assert handoff["event_name"] == CANONICAL_EVENT_NAME
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["payload"]["query"] == "cid:sample"
    assert handoff["normalized_intent"]["method"] == "invoke_service"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "DISPLAY_WIDGET_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | DISPLAY_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["DISPLAY_WIDGET_BRIDGE_OPERATIONS"]) == DISPLAY_WIDGET_OPERATIONS
    assert descriptor["runtime_handoff"]["event_name"] == CANONICAL_EVENT_NAME
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert "hallucinate_app_mobile_interop_events" in descriptor["runtime_handoff"][
        "persistence_tables"
    ]
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_module_remains_parseable_after_descriptor_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)" in source


def test_fixture_schema_script_docs_discovery_and_heap_record_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")
    test_interface = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-674",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        CANONICAL_EVENT_NAME,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinate_app_mobile_interop_events",
        "hallucinate_app_mobile_interop_receipts",
    ]
    for content in (docs, discovery, heap, test_interface, schema, script):
        for term in required_terms[:6]:
            assert term in content, f"missing {term!r}"

    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
