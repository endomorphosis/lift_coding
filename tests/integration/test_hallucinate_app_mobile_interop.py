"""Hallucinate App/mobile interoperability regression tests for MGW-579."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ID = "VAIOS-G707"
CONTRACT_ID = "interface contract hallucinate_app mobile"
HANDOFF_EVENT = "hallucinate-app:mobile-interop-handoff"
DESCRIPTOR_ID = "hallucinate-app-mobile-interop@0.1.0"
INTEROP_TABLE = "hallucinate_app_mobile_interop_events"
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
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => {
  classExports.push(name);
  return `class ${name}`;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;\s*$/m, '');
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
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
source = source.replace(/export default\s+[A-Za-z0-9_]+;\s*$/m, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('vector clocks', {
  filter: { mime: 'application/json' },
  result_target: 'mobile_card',
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


def test_hallucinate_app_search_exports_mobile_handoff_descriptor() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_EVENT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
        ],
    )

    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    assert exports["HALLUCINATE_APP_MOBILE_INTEROP_EVENT"] == HANDOFF_EVENT
    assert exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"] == descriptor
    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
    assert descriptor["contract_id"] == CONTRACT_ID
    assert descriptor["source_surface"] == "hallucinate_app"
    assert descriptor["target_surface"] == "mobile"
    assert descriptor["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["operation"] == "invoke_service"
    assert descriptor["event_type"] == HANDOFF_EVENT
    assert descriptor["mobile_descriptor_ref"] == "mobile/src/orb/metaGlassesOrbDescriptors.js"
    assert set(descriptor["required_artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }


def test_hallucinate_app_search_handoff_payload_targets_mobile_orb() -> None:
    handoff = call_search_handoff_builder()

    assert handoff["event_type"] == HANDOFF_EVENT
    assert handoff["descriptor_id"] == DESCRIPTOR_ID
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["source_surface"] == "hallucinate_app"
    assert handoff["target_surface"] == "mobile"
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["operation"] == "invoke_service"
    assert handoff["correlation_id"] == "test-correlation"
    assert handoff["issued_at"] == "2026-07-08T00:00:00Z"
    assert handoff["payload"] == {
        "intent": "hallucinate_app.content_browser.search",
        "query": "vector clocks",
        "filter": {"mime": "application/json"},
        "result_target": "mobile_card",
    }
    assert handoff["normalized_intent"]["target_ref"] == (
        "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert MOBILE_ORB_OPERATIONS.issubset({method["name"] for method in interface["methods"]})
    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
    assert descriptor["runtime_handoff"]["event_type"] == HANDOFF_EVENT
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["control_surface_policy_id"] == (
        "policy:hallucinate-app:mobile-interop"
    )
    assert INTEROP_TABLE in descriptor["runtime_handoff"]["time_series_tables"]
    assert descriptor["validation"] == {
        "task_id": "MGW-579",
        "goal_id": GOAL_ID,
        "objective_gap_ref": (
            "data/meta_glasses_display_widgets/discovery/"
            "2026-07-08-mgw-579-objective-gap-7edb316279e5.md"
        ),
        "validation_repair_ref": (
            "data/meta_glasses_display_widgets/discovery/"
            "2026-07-08-mgw-579-objective-validation-repair.md"
        ),
        "evidence": "objective validation repair",
    }


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert "descriptorRef(\n                HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_test_interface_html_contains_machine_readable_fixture() -> None:
    html = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(.*?)</textarea>',
        html,
        flags=re.S,
    )
    assert match, "missing mobileInteropContract fixture"
    fixture = json.loads(match.group(1))

    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["descriptor_id"] == DESCRIPTOR_ID
    assert fixture["event_type"] == HANDOFF_EVENT
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert "/v1/mobile/orb/register_edge_capabilities" in fixture["routes"]
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert set(fixture["artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }


def test_duckdb_schema_and_script_record_interop_events_table() -> None:
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    assert f"CREATE TABLE IF NOT EXISTS {INTEROP_TABLE}" in schema
    assert "CREATE VIEW IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in schema
    assert CONTRACT_ID in schema
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in schema
    assert f'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "{INTEROP_TABLE}"' in script
    assert (
        'HALLUCINATE_APP_MOBILE_INTEROP_COMPATIBILITY_VIEW = '
        '"hallucinate_app_mobile_interop_receipts"'
    ) in script
    assert CONTRACT_ID in script


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-579-objective-validation-repair.md"
    ).read_text(encoding="utf-8")
    gap = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-579-objective-gap-7edb316279e5.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "MGW-579",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        CONTRACT_ID,
        HANDOFF_EVENT,
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        INTEROP_TABLE,
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content

    assert "7edb316279e5a093e45d963b421d143361ec8d50" in gap
    assert "2026-07-08-mgw-579-objective-validation-repair.md" in heap
