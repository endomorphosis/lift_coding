"""Interoperability tests proving hallucinate_app <-> mobile integration.

These tests satisfy the evidence requirements for VAIOS-G707
("Interoperate hallucinate_app with mobile") and repair the objective
validation gap filed in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-gap-7edb316279e5.md`
(fingerprint `7edb316279e5a093e45d963b421d143361ec8d50`).

They verify that:
1. The Hallucinate App desktop search surface exports a real, importable
   `interface contract hallucinate_app mobile` contract and a handoff
   builder function that produces a normalized envelope.
2. The mobile ORB bridge descriptors export the matching mobile-side
   contract/interface/descriptor, scoped to objective goal `VAIOS-G707`.
3. Both sides agree on the `contract_id`, `control_surface_contract_ref`,
   and routes.
4. The mobile ORB bridge module remains valid ESM and actually wires the new
   descriptor into edge capability registration plus a runtime handoff
   handler (`handleHallucinateAppMobileSearchHandoff`).
5. The DuckDB schema/script pair under `hallucinate_app/ipfs_accelerate_py`
   records matching interop evidence.
6. The Hallucinate App test interface carries a machine-readable fixture of
   the same contract.
7. The objective validation repair is recorded in the discovery evidence
   file and the objective heap.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_ID = "interface contract hallucinate_app mobile"
GOAL_ID = "VAIOS-G707"

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
MOBILE_DESCRIPTORS_PATH = "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_BRIDGE_PATH = "mobile/src/orb/metaGlassesMobileOrbBridge.js"
MOBILE_JEST_TEST_PATH = (
    "mobile/src/orb/__tests__/metaGlassesMobileOrbBridge.hallucinateAppInterop.test.js"
)
DOCS_PATH = "docs/integration/hallucinate_app-mobile.md"
OBJECTIVE_GAP_PATH = (
    "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-gap-7edb316279e5.md"
)
VALIDATION_REPAIR_PATH = (
    "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md"
)
HEAP_PATH = "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"

# Shared transform: rewrite `export const`/`export function`/`export class`
# statements into plain assignments/declarations attached to `exports`, so an
# ES module can be executed inside a Node `vm` context without a bundler.
_JS_EXPORT_TRANSFORM = r"""
function transform(source) {
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
  source = source.replace(/export default\s+[A-Za-z0-9_.]+;?/g, '');
  source += '\n' + functionExports.map((n) => `exports.${n} = ${n};`).join('\n');
  source += '\n' + classExports.map((n) => `exports.${n} = ${n};`).join('\n');
  return source;
}
"""


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def load_js_exports(path: str, export_names: list[str]) -> dict:
    """Load JSON-serializable named exports from a standalone ES module."""
    script = _JS_EXPORT_TRANSFORM + r"""
const fs = require('fs');
const vm = require('vm');
const filePath = process.argv[1];
const requested = JSON.parse(process.argv[2]);
const source = transform(fs.readFileSync(filePath, 'utf8'));
const context = { exports: {}, module: { exports: {} }, require, console };
vm.createContext(context);
vm.runInContext(source, context, { filename: filePath });
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


def call_js_export(path: str, export_name: str, args: list) -> dict:
    """Call an exported function from a standalone ES module and return its result."""
    script = _JS_EXPORT_TRANSFORM + r"""
const fs = require('fs');
const vm = require('vm');
const filePath = process.argv[1];
const exportName = process.argv[2];
const callArgs = JSON.parse(process.argv[3]);
const source = transform(fs.readFileSync(filePath, 'utf8'));
const context = { exports: {}, module: { exports: {} }, require, console };
vm.createContext(context);
vm.runInContext(source, context, { filename: filePath });
const fn = context.exports[exportName];
if (typeof fn !== 'function') {
  throw new Error(`Export ${exportName} is not a function in ${filePath}`);
}
const result = fn(...callArgs);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), export_name, json.dumps(args)],
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


class TestHallucinateAppSearchInterfaceContract:
    """Prove the desktop half of the interop contract is real and importable."""

    def test_search_interface_exports_interop_contract(self):
        exports = load_js_exports(
            SEARCH_INTERFACE_PATH,
            ["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"],
        )
        contract = exports["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]

        assert contract["contract_id"] == CONTRACT_ID
        assert contract["source_surface"] == "hallucinate_app"
        assert contract["target_surface"] == "mobile"
        assert contract["route"] == "/v1/mobile/orb/invoke_service"
        assert contract["operation"] == "invoke_service"
        assert contract["descriptor_path"] == SEARCH_INTERFACE_PATH
        assert set(contract["required_artifacts"]) == {
            "interaction_envelope",
            "policy_decision",
            "mediation_receipt",
        }

    def test_build_hallucinate_app_mobile_search_handoff_produces_normalized_envelope(self):
        result = call_js_export(
            SEARCH_INTERFACE_PATH,
            "buildHallucinateAppMobileSearchHandoff",
            [
                "stable diffusion checkpoints",
                {
                    "correlation_id": "test-hallucinate-app-mobile-search-1",
                    "issued_at": "2026-07-08T00:00:00.000Z",
                    "result_target": "mobile_card",
                },
            ],
        )

        assert result["contract_id"] == CONTRACT_ID
        assert result["source_surface"] == "hallucinate_app"
        assert result["target_surface"] == "mobile"
        assert result["route"] == "/v1/mobile/orb/invoke_service"
        assert result["correlation_id"] == "test-hallucinate-app-mobile-search-1"
        assert result["payload"]["query"] == "stable diffusion checkpoints"
        assert result["payload"]["result_target"] == "mobile_card"
        assert result["normalized_intent"]["method"] == "invoke_service"
        assert result["normalized_intent"]["target_ref"] == (
            "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service"
        )
        assert result["normalized_intent"]["arguments"]["query"] == (
            "stable diffusion checkpoints"
        )


class TestMobileDescriptorContract:
    """Prove the mobile-side descriptor mirrors the desktop contract."""

    def test_mobile_descriptor_exports_hallucinate_app_interop_contract(self):
        exports = load_js_exports(
            MOBILE_DESCRIPTORS_PATH,
            [
                "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
                "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
                "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
                "MOBILE_ORB_BRIDGE_OPERATIONS",
                "DISPLAY_WIDGET_BRIDGE_OPERATIONS",
            ],
        )
        contract = exports["HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT"]
        interface = exports["HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE"]
        descriptor = exports["HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"]
        mobile_ops = set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"])
        display_ops = set(exports["DISPLAY_WIDGET_BRIDGE_OPERATIONS"])

        assert contract["contract_id"] == CONTRACT_ID
        assert contract["source_surface"] == "hallucinate_app"
        assert contract["target_surface"] == "mobile"

        assert interface["metadata"]["interface_contract"] == CONTRACT_ID
        assert interface["objective_goals"] == [GOAL_ID]
        assert {method["name"] for method in interface["methods"]} == (mobile_ops | display_ops)

        assert descriptor["schema_refs"]["search_interface"] == SEARCH_INTERFACE_PATH
        assert descriptor["schema_refs"]["test_interface"] == TEST_INTERFACE_PATH
        assert descriptor["schema_refs"]["time_series_schema"] == TIME_SERIES_SCHEMA_PATH
        assert descriptor["schema_refs"]["benchmark_schema_script"] == (
            BENCHMARK_SCHEMA_SCRIPT_PATH
        )
        assert descriptor["runtime_handoff"]["source_surface"] == "hallucinate_app"
        assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
        assert descriptor["runtime_handoff"]["duckdb_receipt_table"] == (
            "hallucinate_app_mobile_interop_receipts"
        )
        assert descriptor["validation"]["task_id"] == "MGW-579"
        assert descriptor["validation"]["goal_id"] == GOAL_ID
        assert descriptor["validation"]["evidence"] == "objective validation repair"
        assert descriptor["validation"]["objective_gap_ref"] == OBJECTIVE_GAP_PATH
        assert descriptor["validation"]["validation_repair_ref"] == VALIDATION_REPAIR_PATH

    def test_mobile_contract_matches_hallucinate_app_desktop_contract(self):
        desktop = load_js_exports(
            SEARCH_INTERFACE_PATH,
            ["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"],
        )["HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"]
        mobile = load_js_exports(
            MOBILE_DESCRIPTORS_PATH,
            ["HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT"],
        )["HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT"]

        assert desktop["contract_id"] == mobile["contract_id"]
        assert desktop["control_surface_contract_ref"] == mobile["control_surface_contract_ref"]
        assert desktop["route"] in mobile["routes"]
        assert desktop["source_surface"] == mobile["source_surface"]
        assert desktop["target_surface"] == mobile["target_surface"]
        assert set(desktop["required_artifacts"]) == set(mobile["artifacts"])


class TestMobileOrbBridgeWiring:
    """Prove the mobile ORB bridge actually wires in the new descriptor/handler."""

    def test_bridge_module_remains_parseable_after_contract_wiring(self):
        assert_module_is_valid_esm(MOBILE_BRIDGE_PATH)

    def test_bridge_imports_and_advertises_hallucinate_app_descriptor(self):
        source = _read(MOBILE_BRIDGE_PATH)
        assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT" in source
        assert "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE" in source
        assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
        assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1

    def test_bridge_defines_runtime_handoff_method(self):
        source = _read(MOBILE_BRIDGE_PATH)
        assert source.count("async handleHallucinateAppMobileSearchHandoff(") == 1
        assert "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.contract_id" in source

    def test_jest_regression_test_exists_for_runtime_handoff(self):
        source = _read(MOBILE_JEST_TEST_PATH)
        assert "handleHallucinateAppMobileSearchHandoff" in source
        assert "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" in source
        assert "invoke_service" in source
        assert "dispatchGlassesResponse" in source


class TestDuckDBSchemaEvidence:
    """Prove the DuckDB schema/script pair records matching interop evidence."""

    def test_time_series_schema_declares_hallucinate_app_mobile_interop_receipts(self):
        source = _read(TIME_SERIES_SCHEMA_PATH)
        assert "hallucinate_app_mobile_interop_receipts" in source
        assert CONTRACT_ID in source
        assert GOAL_ID in source

    def test_benchmark_schema_script_mirrors_interop_constants(self):
        source = _read(BENCHMARK_SCHEMA_SCRIPT_PATH)
        assert (
            'HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID = "interface contract hallucinate_app mobile"'
            in source
        )
        assert 'HALLUCINATE_APP_MOBILE_INTEROP_TABLE = "hallucinate_app_mobile_interop_receipts"' in (
            source
        )
        assert "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES" in source
        assert "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS" in source
        assert GOAL_ID in source


class TestHallucinateAppTestInterfaceFixture:
    """Prove the Electron test interface carries a machine-readable fixture."""

    def test_test_interface_carries_machine_readable_fixture(self):
        source = _read(TEST_INTERFACE_PATH)
        assert f'data-contract-id="{CONTRACT_ID}"' in source
        assert f'"contract_id": "{CONTRACT_ID}"' in source
        assert "/v1/mobile/orb/invoke_service" in source
        assert "/v1/mobile/orb/diagnostics" in source


class TestDocsAndDiscoveryEvidence:
    """Prove docs, discovery evidence, and the objective heap stay aligned."""

    REQUIRED_TERMS = [
        "MGW-579",
        "VAIOS-G707",
        "interface contract hallucinate_app mobile",
        "objective validation repair",
        "objective/interoperability/hallucinate_app-mobile",
        "tests/integration/test_hallucinate_app_mobile_interop.py",
        "docs/integration/hallucinate_app-mobile.md",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/orb/metaGlassesMobileOrbBridge.js",
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "hallucinate_app_mobile_interop_receipts",
    ]

    def test_docs_and_validation_repair_cover_required_terms(self):
        docs = _read(DOCS_PATH)
        repair = _read(VALIDATION_REPAIR_PATH)

        for term in self.REQUIRED_TERMS:
            assert term in docs, f"{term!r} missing from {DOCS_PATH}"
            assert term in repair, f"{term!r} missing from {VALIDATION_REPAIR_PATH}"

    def test_objective_heap_records_this_validation_repair(self):
        heap = _read(HEAP_PATH)

        for term in self.REQUIRED_TERMS:
            assert term in heap, f"{term!r} missing from {HEAP_PATH}"
        assert VALIDATION_REPAIR_PATH in heap

    def test_objective_gap_fingerprint_is_recorded(self):
        gap = _read(OBJECTIVE_GAP_PATH)
        repair = _read(VALIDATION_REPAIR_PATH)

        fingerprint = "7edb316279e5a093e45d963b421d143361ec8d50"
        assert fingerprint in gap
        assert fingerprint in repair
        assert "Goal id: VAIOS-G707" in gap
