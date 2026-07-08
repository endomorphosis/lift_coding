"""Hallucinate App/mobile interoperability regression tests for MGW-579."""

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
    GOAL_ID,
    INTERFACE_CONTRACT,
    REQUIRED_ARTIFACT_REFS,
    REQUIRED_MOBILE_ORB_ROUTES,
    REQUIRED_RECEIPT_TABLE,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_search_handoff,
    discover_hallucinate_app_mobile_contract,
)

TASK_ID = "MGW-579"


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
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  functionExports.push(name);
  return `class ${name} `;
});
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = {
  exports: {},
  console,
  Date,
  localStorage: undefined,
  document: undefined,
};
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


def test_discover_hallucinate_app_mobile_contract_finds_all_evidence_paths() -> None:
    contract = discover_hallucinate_app_mobile_contract(REPO_ROOT)

    assert contract.interface_contract == INTERFACE_CONTRACT
    assert contract.goal_id == GOAL_ID
    assert contract.task_id == TASK_ID
    assert set(contract.routes) == set(REQUIRED_MOBILE_ORB_ROUTES)
    assert set(contract.artifact_refs) == set(REQUIRED_ARTIFACT_REFS)
    assert contract.receipt_table == REQUIRED_RECEIPT_TABLE
    assert {
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
    }.issubset(set(contract.exported_symbols))
    assert contract.search_interface_path.endswith(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
    )
    assert contract.time_series_schema_path.endswith(
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    )


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    try:
        discover_hallucinate_app_mobile_contract(tmp_path / "missing")
    except HallucinateAppMobileInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_search_handoff_is_deterministic() -> None:
    first = build_hallucinate_app_mobile_search_handoff(
        REPO_ROOT,
        query="open latest benchmark card",
        filter={"mimetype": "application/json"},
    )
    second = build_hallucinate_app_mobile_search_handoff(
        REPO_ROOT,
        query="open latest benchmark card",
        filter={"mimetype": "application/json"},
    )

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.goal_id == GOAL_ID
    assert first.task_id == TASK_ID
    assert first.source_surface == "hallucinate_app"
    assert first.target_surface == "mobile"
    assert first.route == "/v1/mobile/orb/invoke_service"
    assert first.operation == "invoke_service"
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(first.artifact_refs) == set(REQUIRED_ARTIFACT_REFS)
    assert first.receipt_table == REQUIRED_RECEIPT_TABLE


def test_hallucinate_search_interface_exports_mobile_handoff_descriptor() -> None:
    exports = load_js_exports(
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        [
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "buildHallucinateAppMobileSearchHandoff",
        ],
    )

    contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert contract["contract_id"] == INTERFACE_CONTRACT
    assert contract["source_surface"] == "hallucinate_app"
    assert contract["target_surface"] == "mobile"
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert set(contract["required_artifacts"]) == set(REQUIRED_ARTIFACT_REFS)
    assert descriptor["goal_id"] == GOAL_ID
    assert descriptor["task_id"] == TASK_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"

    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  return `exports.${name} = function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, 'class $1 ');
source = source.replace(/export default\s+[A-Za-z0-9_]+;?/g, '');
const context = { exports: {}, console, Date };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('cid query', {
  filter: { mimetype: 'text/plain' },
  result_target: 'mobile_card',
  correlation_id: 'corr-mgw-579',
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
    handoff = json.loads(result.stdout)
    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert handoff["correlation_id"] == "corr-mgw-579"
    assert handoff["payload"]["query"] == "cid query"
    assert handoff["normalized_intent"]["method"] == "invoke_service"


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS",
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ],
    )

    operations = exports["HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS"]
    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert set(operations) == {
        "register_edge_capabilities",
        "invoke_service",
        "dispatch_glasses_response",
        "diagnostics",
    }
    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert GOAL_ID in interface["objective_goals"]
    assert {method["name"] for method in interface["methods"]} == set(operations)
    assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert descriptor["runtime_handoff"]["event_name"] == "hallucinate_app-mobile:handoff"
    assert descriptor["runtime_handoff"]["receipt_table"] == REQUIRED_RECEIPT_TABLE
    assert set(descriptor["runtime_handoff"]["artifact_refs"]) == set(REQUIRED_ARTIFACT_REFS)
    assert descriptor["validation"]["task_id"] == TASK_ID
    assert descriptor["validation"]["goal_id"] == GOAL_ID
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppMobileInteropInterfaceCid" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_hallucinate_test_interface_and_duckdb_schema_record_contract() -> None:
    html = (
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

    assert INTERFACE_CONTRACT in html
    assert "mobileInteropContract" in html
    assert "mobileInteropResults" in html
    for route in REQUIRED_MOBILE_ORB_ROUTES:
        assert route in html

    assert REQUIRED_RECEIPT_TABLE in schema
    assert INTERFACE_CONTRACT in schema
    assert "idx_hallucinate_app_mobile_interop_receipts_route" in schema

    assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID" in script
    assert "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES" in script
    assert REQUIRED_RECEIPT_TABLE in script


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
        TASK_ID,
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
