"""Hallucinate App/mobile interoperability regression tests for MGW-579."""

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
HANDOFF_EVENT = "hallucinate-app:mobile-interop-handoff"
RECEIPT_TABLE = "hallucinate_app_mobile_interop_receipts"
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
SEARCH_HANDOFF_OPERATIONS = {
    "handoff_content_search",
    "render_mobile_search_result",
    "dispatch_glasses_response",
    "diagnostics",
}


def evaluate_js_module(path: str, body: str) -> object:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const body = process.argv[2];
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
const result = Function('exports', body)(context.exports);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), body],
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


def read_html_contract_fixture() -> dict:
    source = (
        REPO_ROOT / "hallucinate_app/hallucinate_app/node/views/test_interface.html"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'<textarea id="mobileInteropContract"[^>]*>(.*?)</textarea>',
        source,
        re.DOTALL,
    )
    assert match, "missing mobileInteropContract fixture"
    return json.loads(html.unescape(match.group(1)))


def test_search_interface_builds_mobile_handoff_payload_and_emits_event() -> None:
    result = evaluate_js_module(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        f"""
const descriptor = exports.HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR;
const handoff = exports.buildHallucinateAppMobileSearchHandoff('edge photos', {{
  filter: {{ mimetype: 'image/jpeg' }},
  result_target: 'meta_glasses_card',
  correlation_id: 'corr-mgw-579',
  issued_at: '2026-07-08T00:00:00.000Z',
}});
const events = [];
const eventBus = {{ emit: (name, payload) => events.push([name, payload]) }};
const search = new exports.SearchInterface({{ eventBus }});
search.currentFilter = {{ tag: 'field-test' }};
search.on('mobile-handoff', (payload) => events.push(['direct:mobile-handoff', payload]));
search.search('field test');
return {{ descriptor, handoff, events }};
""",
    )

    descriptor = result["descriptor"]
    handoff = result["handoff"]
    event_names = [event[0] for event in result["events"]]
    emitted_handoff = next(
        payload for name, payload in result["events"] if name == HANDOFF_EVENT
    )

    assert descriptor["interface_contract"] == CONTRACT_ID
    assert descriptor["goal_id"] == GOAL_ID
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["source_surface"] == "hallucinate_app"
    assert handoff["target_surface"] == "mobile"
    assert handoff["event_name"] == HANDOFF_EVENT
    assert handoff["route"] == "/v1/mobile/orb/invoke_service"
    assert handoff["operation"] == "invoke_service"
    assert handoff["payload"] == {
        "intent": "hallucinate_app.content_browser.search",
        "query": "edge photos",
        "filter": {"mimetype": "image/jpeg"},
        "result_target": "meta_glasses_card",
    }
    assert handoff["normalized_intent"]["target_ref"].endswith(
        "mobile_orb_bridge.invoke_service"
    )
    assert HANDOFF_EVENT in event_names
    assert "hallucinate_app-mobile:handoff" in event_names
    assert "direct:mobile-handoff" in event_names
    assert emitted_handoff["contract_id"] == CONTRACT_ID
    assert emitted_handoff["payload"]["filter"] == {"tag": "field-test"}


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = evaluate_js_module(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        """
return {
  interface: exports.HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE,
  descriptor: exports.HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR,
  mobileOperations: exports.MOBILE_ORB_BRIDGE_OPERATIONS,
  searchOperations: exports.HALLUCINATE_APP_MOBILE_SEARCH_OPERATIONS,
  localKey: exports.localInterfaceKey(exports.HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE),
};
""",
    )

    interface = exports["interface"]
    descriptor = exports["descriptor"]

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert interface["objective_goals"] == [GOAL_ID]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | SEARCH_HANDOFF_OPERATIONS
    )
    assert set(exports["mobileOperations"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["searchOperations"]) == SEARCH_HANDOFF_OPERATIONS
    assert exports["localKey"] == (
        "handsfree.interop.hallucinate_app_mobile."
        "hallucinate_app_mobile_interop@0.1.0"
    )
    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["runtime_handoff"]["event_name"] == HANDOFF_EVENT
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["runtime_handoff"]["receipt_table"] == RECEIPT_TABLE
    assert set(descriptor["runtime_handoff"]["required_artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }
    assert descriptor["validation"]["task_id"] == "MGW-579"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert "descriptorRef(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_test_interface_fixture_and_duckdb_receipts_match_contract() -> None:
    fixture = read_html_contract_fixture()
    schema = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    assert fixture["contract_id"] == CONTRACT_ID
    assert fixture["source_surface"] == "hallucinate_app"
    assert fixture["target_surface"] == "mobile"
    assert fixture["event_name"] == HANDOFF_EVENT
    assert "/v1/mobile/orb/invoke_service" in fixture["routes"]
    assert fixture["receipt_table"] == RECEIPT_TABLE
    assert set(fixture["artifacts"]) == {
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    }
    assert f"CREATE TABLE IF NOT EXISTS {RECEIPT_TABLE}" in schema
    assert f"DEFAULT '{CONTRACT_ID}'" in schema
    assert "source_surface VARCHAR NOT NULL DEFAULT 'hallucinate_app'" in schema
    assert "target_surface VARCHAR NOT NULL DEFAULT 'mobile'" in schema
    assert f'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "{RECEIPT_TABLE}"' in script
    assert f'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "{CONTRACT_ID}"' in script
    assert '"/v1/mobile/orb/invoke_service"' in script


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
        CONTRACT_ID,
        HANDOFF_EVENT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        RECEIPT_TABLE,
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content
