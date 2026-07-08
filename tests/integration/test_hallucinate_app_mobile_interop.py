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
    GOAL_ID,
    INTERFACE_CONTRACT,
    REQUIRED_HALLUCINATE_APP_ARTIFACTS,
    REQUIRED_MOBILE_ORB_OPERATIONS,
    HallucinateAppMobileInteropError,
    build_hallucinate_app_mobile_search_handoff,
    discover_hallucinate_app_mobile_contract,
)

HALLUCINATE_APP_ROOT = REPO_ROOT / "hallucinate_app"
MOBILE_ROOT = REPO_ROOT / "mobile"


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
source = source.replace(/export default\s+([A-Za-z0-9_]+)\s*;?/g, (_, name) => {
  return `exports.default = ${name};`;
});
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


def assert_module_is_valid_esm(path: str) -> None:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_discover_hallucinate_app_mobile_contract_finds_required_artifacts() -> None:
    contract = discover_hallucinate_app_mobile_contract(HALLUCINATE_APP_ROOT, MOBILE_ROOT)

    assert contract.receipt_table == "hallucinate_app_mobile_interop_receipts"
    assert contract.search_handoff_event == "hallucinate-app:mobile-interop-handoff"
    assert set(contract.mobile_orb_operations) == set(REQUIRED_MOBILE_ORB_OPERATIONS)
    assert set(contract.artifact_refs) == set(REQUIRED_HALLUCINATE_APP_ARTIFACTS)
    assert any(path.endswith("search_interface.js") for path in contract.hallucinate_app_descriptor_paths)
    assert any(path.endswith("metaGlassesOrbDescriptors.js") for path in contract.mobile_descriptor_paths)


def test_discover_hallucinate_app_mobile_contract_raises_for_missing_root(tmp_path) -> None:
    try:
        discover_hallucinate_app_mobile_contract(tmp_path / "missing", MOBILE_ROOT)
    except HallucinateAppMobileInteropError as exc:
        assert "root not found" in str(exc)
    else:
        raise AssertionError("expected HallucinateAppMobileInteropError")


def test_build_hallucinate_app_mobile_search_handoff_is_deterministic() -> None:
    first = build_hallucinate_app_mobile_search_handoff(
        HALLUCINATE_APP_ROOT,
        MOBILE_ROOT,
        query="gpu benchmark",
        filter={"mimetype": "application/json"},
    )
    second = build_hallucinate_app_mobile_search_handoff(
        HALLUCINATE_APP_ROOT,
        MOBILE_ROOT,
        query="gpu benchmark",
        filter={"mimetype": "application/json"},
    )

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == INTERFACE_CONTRACT
    assert first.goal_id == GOAL_ID
    assert first.task_id == "VAI-674"
    assert first.bundle == "objective/interoperability/hallucinate_app-mobile"
    assert first.source_repository == "hallucinate_app"
    assert first.target_repository == "mobile"
    assert first.operation == "invoke_service"
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(first.mobile_orb_operations) == set(REQUIRED_MOBILE_ORB_OPERATIONS)
    assert set(first.artifact_refs) == set(REQUIRED_HALLUCINATE_APP_ARTIFACTS)


def test_hallucinate_app_search_interface_exports_handoff_descriptor() -> None:
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
    assert contract["route"] == "/v1/mobile/orb/invoke_service"
    assert contract["operation"] == "invoke_service"
    assert descriptor["goal_id"] == GOAL_ID
    assert descriptor["task_id"] == "VAI-674"
    assert descriptor["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_hallucinate_app_search_handoff_builder_emits_mobile_payload() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let source = fs.readFileSync(path, 'utf8');
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  return `function ${name}(`;
});
source = source.replace(/export class\s+([A-Za-z0-9_]+)\s*/g, (_, name) => {
  return `class ${name} `;
});
source = source.replace(/export default\s+([A-Za-z0-9_]+)\s*;?/g, (_, name) => {
  return `exports.default = ${name};`;
});
source = `${source}
exports.buildHallucinateAppMobileSearchHandoff = buildHallucinateAppMobileSearchHandoff;`;
const context = { exports: {}, console, Date };
vm.runInNewContext(source, context, { filename: path });
const handoff = context.exports.buildHallucinateAppMobileSearchHandoff('gpu benchmark', {
  filter: { mimetype: 'application/json' },
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
            str(REPO_ROOT / "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    handoff = json.loads(result.stdout)

    assert handoff["contract_id"] == INTERFACE_CONTRACT
    assert handoff["descriptor_id"] == "hallucinate-app-mobile-interop@0.1.0"
    assert handoff["goal_id"] == GOAL_ID
    assert handoff["validation"]["evidence"] == "objective validation repair"
    assert handoff["normalized_intent"]["method"] == "invoke_service"
    assert handoff["payload"]["query"] == "gpu benchmark"
    assert handoff["payload"]["filter"] == {"mimetype": "application/json"}


def test_mobile_descriptor_exports_hallucinate_app_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == INTERFACE_CONTRACT
    assert interface["metadata"]["goal_id"] == GOAL_ID
    assert interface["metadata"]["source_surface"] == "hallucinate_app"
    assert interface["metadata"]["target_surface"] == "mobile"
    assert GOAL_ID in interface["objective_goals"]
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == set(REQUIRED_MOBILE_ORB_OPERATIONS)
    assert {
        "hallucinate_app.content_browser.search",
        "hallucinate_app.content_browser.filter",
        "hallucinate_app.content_browser.clear_search",
    } == set(exports["HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS"])
    assert descriptor["schema_refs"] == {
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
        "mobile_orb_bridge": "mobile/src/orb/metaGlassesMobileOrbBridge.js",
    }
    assert descriptor["runtime_handoff"]["event_name"] == "hallucinate-app:mobile-interop-handoff"
    assert descriptor["runtime_handoff"]["receipt_table"] == "hallucinate_app_mobile_interop_receipts"
    assert descriptor["validation"]["task_id"] == "VAI-674"
    assert descriptor["validation"]["evidence"] == "objective validation repair"


def test_mobile_orb_bridge_advertises_hallucinate_app_descriptor() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )

    assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
    assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "hallucinateAppInteropInterfaceCid" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_schema_fixture_docs_discovery_and_heap_record_objective_validation_repair() -> None:
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
    schema_sql = (
        REPO_ROOT / "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
    ).read_text(encoding="utf-8")
    benchmark_script = (
        REPO_ROOT
        / "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
    ).read_text(encoding="utf-8")

    required_terms = [
        "VAI-674",
        GOAL_ID,
        "objective/interoperability/hallucinate_app-mobile",
        "objective validation repair",
        INTERFACE_CONTRACT,
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "src/handsfree/hallucinate_app_mobile_interop.py",
        "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js",
        "hallucinate_app/hallucinate_app/node/views/test_interface.html",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
        "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
        "hallucinate_app_mobile_interop_receipts",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"

    for content in (test_interface, schema_sql, benchmark_script):
        assert INTERFACE_CONTRACT in content
        assert "objective validation repair" in content
