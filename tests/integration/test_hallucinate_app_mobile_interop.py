"""Hallucinate App / mobile interoperability repair tests for VAI-684."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOAL_ID = "VAIOS-G707"
CONTRACT_ID = "interface contract hallucinate_app mobile"
SEARCH_INTERFACE_PATH = (
    "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
TEST_INTERFACE_PATH = "hallucinate_app/hallucinate_app/node/views/test_interface.html"
TIME_SERIES_SCHEMA_PATH = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
BENCHMARK_SCHEMA_SCRIPT_PATH = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)

MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
SEARCH_WIDGET_OPERATIONS = {
    "render_content_search_results",
    "update_content_search_results",
    "open_content_search_result",
    "sync_content_search_filter",
}
SEARCH_WIDGET_ACTION_IDS = {
    "mobile_render_content_search_results",
    "mobile_update_content_search_results",
    "mobile_open_content_search_result",
    "mobile_sync_content_search_filter",
}


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const deferredExports = [];
source = source.replace(/export default\s+[A-Za-z0-9_]+;\s*/g, '');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  deferredExports.push(name);
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)/g, (_, name) => {
  deferredExports.push(name);
  return `class ${name}`;
});
source = `${source}\n${deferredExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
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


def assert_module_is_valid_esm(path: str) -> None:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_expected_hallucinate_app_mobile_artifacts_exist() -> None:
    for relative_path in [
        SEARCH_INTERFACE_PATH,
        TEST_INTERFACE_PATH,
        TIME_SERIES_SCHEMA_PATH,
        BENCHMARK_SCHEMA_SCRIPT_PATH,
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        "docs/integration/hallucinate_app-mobile.md",
    ]:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_hallucinate_app_search_interface_builds_mobile_orb_handoff() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
source = source.replace(/export default\s+[A-Za-z0-9_]+;\s*/g, '');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => `const ${name} = exports.${name} =`);
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => `function ${name}(`);
source = source.replace(/export class\s+SearchInterface/g, 'class SearchInterface');
source += '\nexports.buildHallucinateAppMobileSearchHandoff = buildHallucinateAppMobileSearchHandoff;';
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('pyarrow dashboard', {
  filter: { mimetype: 'application/json' },
  result_target: 'mobile_card',
  correlation_id: 'vai-684-correlation',
  issued_at: '2026-07-08T21:00:00.000Z',
});
process.stdout.write(JSON.stringify({
  contract: context.exports.HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT,
  handoff,
}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / SEARCH_INTERFACE_PATH)],
        check=True,
        text=True,
        capture_output=True,
    )
    probe = json.loads(result.stdout)
    contract = probe["contract"]
    handoff = probe["handoff"]

    assert contract["contract_id"] == CONTRACT_ID
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert handoff["contract_id"] == CONTRACT_ID
    assert handoff["correlation_id"] == "vai-684-correlation"
    assert handoff["payload"] == {
        "intent": "hallucinate_app.content_browser.search",
        "query": "pyarrow dashboard",
        "filter": {"mimetype": "application/json"},
        "result_target": "mobile_card",
    }
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert (
        handoff["normalized_intent"]["target_ref"]
        == "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
    )


def test_hallucinate_app_search_interface_emits_mobile_handoff_event() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
source = source.replace(/export default\s+[A-Za-z0-9_]+;\s*/g, '');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => `const ${name} = exports.${name} =`);
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => `function ${name}(`);
source = source.replace(/export class\s+SearchInterface/g, 'class SearchInterface');
source += '\nexports.SearchInterface = SearchInterface;';
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const events = [];
const listeners = [];
const search = new context.exports.SearchInterface({
  eventBus: {
    emit: (event, payload) => events.push({ event, payload }),
  },
  bridge: {},
});
search.on('mobile-handoff', (payload) => listeners.push(payload));
search.applyFilter({ tags: ['vai-684'] });
search.search('mobile handoff');
process.stdout.write(JSON.stringify({ events, listeners }));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / SEARCH_INTERFACE_PATH)],
        check=True,
        text=True,
        capture_output=True,
    )
    probe = json.loads(result.stdout)
    handoff_event = next(
        event for event in probe["events"] if event["event"] == "hallucinate_app-mobile:handoff"
    )

    assert handoff_event["payload"]["contract_id"] == CONTRACT_ID
    assert handoff_event["payload"]["payload"]["query"] == "mobile handoff"
    assert handoff_event["payload"]["payload"]["filter"] == {"tags": ["vai-684"]}
    assert probe["listeners"][0]["contract_id"] == CONTRACT_ID


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_SEARCH_WIDGET_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == CONTRACT_ID
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | SEARCH_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["HALLUCINATE_APP_MOBILE_SEARCH_WIDGET_OPERATIONS"]) == (
        SEARCH_WIDGET_OPERATIONS
    )
    assert descriptor["schema_refs"] == {
        "search_interface": SEARCH_INTERFACE_PATH,
        "test_interface": TEST_INTERFACE_PATH,
        "time_series_schema": TIME_SERIES_SCHEMA_PATH,
        "benchmark_schema_script": BENCHMARK_SCHEMA_SCRIPT_PATH,
        "search_widget_contract": "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
    }
    assert descriptor["runtime_handoff"]["route"] == "/v1/mobile/orb/invoke_service"
    assert descriptor["runtime_handoff"]["operation"] == "invoke_service"
    assert descriptor["runtime_handoff"]["time_series_table"] == (
        "hallucinate_app_mobile_interop_receipts"
    )
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["repair_task_id"] == "VAI-684"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_search_widget_contract_maps_actions_to_dat_methods() -> None:
    exports = load_js_exports(
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        [
            "HALLUCINATE_APP_SEARCH_WIDGET_ACTION_IDS",
            "HALLUCINATE_APP_SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_WIDGET_RESULT_TARGET_BY_ACTION_ID",
            "HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT",
        ],
    )
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => `const ${name} = exports.${name} =`);
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => `function ${name}(`);
source += '\nexports.buildHallucinateAppSearchWidgetAction = buildHallucinateAppSearchWidgetAction;';
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const action = context.exports.buildHallucinateAppSearchWidgetAction(
  'mobile_render_content_search_results',
  { query: 'cid' },
);
process.stdout.write(JSON.stringify(action));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(REPO_ROOT / "mobile/src/utils/hallucinateAppSearchWidgetContract.js"),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    action = json.loads(result.stdout)
    contract = exports["HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT"]

    assert set(exports["HALLUCINATE_APP_SEARCH_WIDGET_ACTION_IDS"]) == SEARCH_WIDGET_ACTION_IDS
    assert set(exports["HALLUCINATE_APP_SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID"]) == (
        SEARCH_WIDGET_ACTION_IDS
    )
    assert set(exports["HALLUCINATE_APP_SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID"]) == (
        SEARCH_WIDGET_ACTION_IDS
    )
    assert set(exports["HALLUCINATE_APP_SEARCH_WIDGET_RESULT_TARGET_BY_ACTION_ID"]) == (
        SEARCH_WIDGET_ACTION_IDS
    )
    assert contract["producer"] == "hallucinate_app"
    assert contract["consumer"] == "mobile"
    assert contract["interface_contract"] == CONTRACT_ID
    assert contract["goal_id"] == GOAL_ID
    assert contract["repair_task_id"] == "VAI-684"
    assert contract["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert action["operation"] == "render_content_search_results"
    assert action["dat_method"] == "renderContentSearchResults"
    assert action["result_target"] == "mobile_card"
    assert action["payload"] == {"query": "cid"}


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "const hallucinateAppInteropInterfaceCid = localInterfaceKey(" in source
    assert "this.localInterfaceCids[4]" in source
    assert "interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source


def test_hallucinate_app_test_interface_and_duckdb_schema_expose_receipt_fixture() -> None:
    html = (REPO_ROOT / TEST_INTERFACE_PATH).read_text(encoding="utf-8")
    schema = (REPO_ROOT / TIME_SERIES_SCHEMA_PATH).read_text(encoding="utf-8")
    script = (REPO_ROOT / BENCHMARK_SCHEMA_SCRIPT_PATH).read_text(encoding="utf-8")

    assert 'id="hallucinate-app-mobile-interop-contract"' in html
    assert f'data-contract-id="{CONTRACT_ID}"' in html
    assert "/v1/mobile/orb/invoke_service" in html
    assert "hallucinate_app_mobile_interop_receipts" in schema
    assert "idx_hallucinate_app_mobile_interop_receipts_route" in schema
    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES" in script


def test_docs_discovery_heap_and_retry_budget_record_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/hallucinate_app-mobile.md").read_text(
        encoding="utf-8"
    )
    discovery = (
        REPO_ROOT
        / "data/virtual_ai_os/discovery/2026-07-08-vai-684-vai-674-validation-repair.md"
    ).read_text(encoding="utf-8")
    retry_budget = (
        REPO_ROOT
        / "data/virtual_ai_os/state/discovery/2026-07-08-vai-684-vai-674-retry-budget.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-684",
        "VAI-674",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        CONTRACT_ID,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        SEARCH_INTERFACE_PATH,
        TEST_INTERFACE_PATH,
        TIME_SERIES_SCHEMA_PATH,
        BENCHMARK_SCHEMA_SCRIPT_PATH,
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/hallucinateAppSearchWidgetContract.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app_mobile_interop_receipts",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    assert "Observed consecutive validation failures: 3" in retry_budget
    assert "python -m pytest tests/integration -q" in retry_budget
