"""Hallucinate App / mobile interoperability regression tests for VAI-674."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOAL_ID = "VAIOS-G707"
INTERFACE_CONTRACT = "interface contract hallucinate_app mobile"
BUNDLE = "objective/interoperability/hallucinate_app-mobile"

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
    "hallucinate_app_content_search",
    "hallucinate_app_content_preview",
    "hallucinate_app_search_result_open",
}
HALLUCINATE_SCHEMA_REFS = {
    "search_interface": (
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    ),
    "test_interface": "hallucinate_app/hallucinate_app/node/views/test_interface.html",
    "time_series_schema": (
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ),
    "benchmark_schema_script": (
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ),
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
source = source.replace(/export default\s+[A-Za-z0-9_]+\s*;?/g, '');
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


def run_hallucinate_app_search_handoff() -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
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
source = source.replace(/export default\s+[A-Za-z0-9_]+\s*;?/g, '');
source = `${source}
${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}
${classExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {}, console };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff(
  'latest benchmark receipts',
  {
    filter: { mimetype: 'application/json' },
    result_target: 'mobile_card',
    correlation_id: 'vai-674-correlation',
    issued_at: '2026-07-08T00:00:00.000Z',
  },
);
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


def test_expected_hallucinate_app_mobile_artifacts_exist() -> None:
    for relative_path in [
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/utils/check_database_schema.py",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/utils/check_db_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    ]:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_hallucinate_app_search_interface_exports_mobile_handoff_descriptor() -> None:
    assert_module_is_valid_esm(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
    handoff = run_hallucinate_app_search_handoff()

    assert contract["contract_id"] == INTERFACE_CONTRACT
    assert contract["objective_goal"] == GOAL_ID
    assert "objective validation repair" in contract["objective_validation_repair"]
    assert descriptor["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert descriptor["interface_contract"] == INTERFACE_CONTRACT
    assert descriptor["schema_refs"] == HALLUCINATE_SCHEMA_REFS
    assert descriptor["runtime_handoff"]["event_type"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"
    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["event_type"] == descriptor["runtime_handoff"]["event_type"]
    assert handoff["descriptor_id"] == descriptor["descriptor_id"]
    assert handoff["payload"]["query"] == "latest benchmark receipts"
    assert handoff["payload"]["filter"] == {"mimetype": "application/json"}
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["normalized_intent"]["arguments"]["result_target"] == "mobile_card"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_SEARCH_OPERATIONS",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["bundle"] == BUNDLE
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | HALLUCINATE_APP_SEARCH_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["HALLUCINATE_APP_MOBILE_SEARCH_OPERATIONS"]) == (
        HALLUCINATE_APP_SEARCH_OPERATIONS
    )
    assert descriptor["schema_refs"] == HALLUCINATE_SCHEMA_REFS
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["event_type"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["runtime_handoff"]["time_series_tables"] == [
        "hallucinate_app_mobile_interop_receipts"
    ]
    assert descriptor["validation"]["task_id"] == "VAI-674"
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
    assert "this.localInterfaceCids[4]" in source


def test_hallucinate_app_mobile_persistence_schema_records_receipts() -> None:
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
        "objective validation repair",
        INTERFACE_CONTRACT,
        "hallucinate_app_mobile_interop_receipts",
        "interaction_envelope",
        "policy_decision",
        "mediation_receipt",
    ]
    for content in (schema, script):
        for term in required_terms:
            assert term in content, f"missing {term!r}"


def test_hallucinate_app_mobile_docs_discovery_and_heap_record_repair() -> None:
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

    required_terms = [
        "VAI-674",
        GOAL_ID,
        BUNDLE,
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-gap-7edb316279e5.md",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    assert "No smaller child goals are required" in discovery
    assert "No smaller child goals are required" in heap
