"""Hallucinate App / mobile interoperability validation for VAI-674."""

from __future__ import annotations

import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOAL_ID = "VAIOS-G707"
CONTRACT_ID = "interface contract hallucinate_app mobile"
DESCRIPTOR_ID = "hallucinate-app-mobile-interop@0.1.0"
HANDOFF_EVENT = "hallucinate-app:mobile-interop-handoff"

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}

HALLUCINATE_APP_SEARCH_OPERATIONS = {
    "forward_content_browser_search",
    "render_content_search_results",
    "open_content_result",
    "acknowledge_mobile_handoff",
}


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


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
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date };
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


def call_js_export(path: str, function_name: str, args: list) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const functionName = process.argv[2];
const args = JSON.parse(process.argv[3]);
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
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console, Date };
vm.runInNewContext(source, context, { filename: path });
process.stdout.write(JSON.stringify(context.exports[functionName](...args)));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), function_name, json.dumps(args)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = read_text(path)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_hallucinate_app_search_handoff_exports_descriptor_and_payload() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    handoff = call_js_export(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "buildHallucinateAppMobileSearchHandoff",
        [
            "vector search",
            {
                "filter": {"mimetype": "application/json"},
                "result_target": "mobile_card",
                "correlation_id": "vai-674-correlation",
                "issued_at": "2026-07-08T00:00:00.000Z",
            },
        ],
    )

    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert set(contract["required_artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }

    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
    assert descriptor["interface_contract"] == CONTRACT_ID
    assert descriptor["goal_id"] == GOAL_ID
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert descriptor["runtime_handoff"]["event_name"] == HANDOFF_EVENT
    assert "hallucinate_app_mobile_interop_events" in descriptor["runtime_handoff"][
        "receipt_tables"
    ]

    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["descriptor_id"] == DESCRIPTOR_ID
    assert handoff["interop_descriptor"]["descriptor_id"] == DESCRIPTOR_ID
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["operation"] == "invoke_service"
    assert handoff["correlation_id"] == "vai-674-correlation"
    assert handoff["payload"] == {
        "intent": "hallucinate_app.content_browser.search",
        "query": "vector search",
        "filter": {"mimetype": "application/json"},
        "result_target": "mobile_card",
    }
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["target_ref"] == (
        "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )


def test_mobile_descriptor_exports_matching_hallucinate_app_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_OPERATIONS",
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
    assert set(exports["HALLUCINATE_APP_MOBILE_SEARCH_OPERATIONS"]) == (
        HALLUCINATE_APP_SEARCH_OPERATIONS
    )
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | HALLUCINATE_APP_SEARCH_OPERATIONS
    )
    assert descriptor["descriptor_id"] == DESCRIPTOR_ID
    assert descriptor["interface"]["metadata"]["interface_contract"] == CONTRACT_ID
    assert descriptor["runtime_handoff"]["event_name"] == HANDOFF_EVENT
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["mobile_orb_methods"] == exports[
        "MOBILE_ORB_BRIDGE_OPERATIONS"
    ]
    assert set(descriptor["runtime_handoff"]["search_methods"]) == (
        HALLUCINATE_APP_SEARCH_OPERATIONS
    )
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = read_text("mobile/src/orb/metaGlassesMobileOrbBridge.js")

    required_terms = [
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinateAppInteropInterfaceCid",
        "localInterfaceKey(",
        "descriptorRef(",
        "this.localInterfaceCids[4]",
    ]
    for term in required_terms:
        assert term in source


def test_hallucinate_app_test_interface_fixture_contains_machine_readable_contract() -> None:
    source = read_text("hallucinate_app/hallucinate_app/node/views/test_interface.html")
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(.*?)</textarea>',
        source,
        flags=re.DOTALL,
    )
    assert match, "mobile interop fixture textarea is missing"

    fixture = json.loads(html.unescape(match.group(1)))
    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["descriptor_id"] == DESCRIPTOR_ID
    assert fixture["goal_id"] == GOAL_ID
    assert fixture["validation_task_id"] == "VAI-674"
    assert fixture["evidence"] == "objective validation repair"
    assert fixture["event_name"] == HANDOFF_EVENT
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert set(fixture["artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }
    assert set(fixture["receipt_tables"]) == {
        "hallucinate_app_mobile_interop_receipts",
        "hallucinate_app_mobile_interop_events",
    }


def test_duckdb_schema_and_benchmark_script_record_interop_evidence() -> None:
    schema = read_text(
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    )
    benchmark = read_text(
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    )

    for content in (schema, benchmark):
        assert CONTRACT_ID in content
        assert "hallucinate_app_mobile_interop_receipts" in content
        assert "hallucinate_app_mobile_interop_events" in content

    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_receipts" in schema
    assert "CREATE TABLE IF NOT EXISTS hallucinate_app_mobile_interop_events" in schema
    assert "HALLUCINATE_APP_MOBILE_INTEROP_EVENTS_TABLE" in benchmark
    assert "HALLUCINATE_APP_MOBILE_INTEROP_TABLES" in benchmark
    assert HANDOFF_EVENT in benchmark
    assert DESCRIPTOR_ID in benchmark


def test_docs_discovery_and_heap_record_vai_674_objective_validation_repair() -> None:
    docs = read_text("docs/integration/hallucinate_app-mobile.md")
    discovery = read_text(
        "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "VAI-674",
        GOAL_ID,
        "objective validation repair",
        CONTRACT_ID,
        DESCRIPTOR_ID,
        HANDOFF_EVENT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app_mobile_interop_receipts",
        "hallucinate_app_mobile_interop_events",
        "No smaller child goals",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content
