"""Interop contract between ``hallucinate_app`` and the mobile client.

MGW-579 repairs the VAIOS-G707 objective validation gap. The contract is kept
static and deterministic so CI can prove the Hallucinate App desktop search
surface, the mobile ORB bridge descriptor, and the nested DuckDB receipt schema
remain aligned without booting Electron, React Native, or DuckDB.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract hallucinate_app mobile"
GOAL_ID = "VAIOS-G707"
TASK_ID = "MGW-579"

HALLUCINATE_APP_SEARCH_INTERFACE = (
    "hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js"
)
HALLUCINATE_APP_TEST_INTERFACE = "hallucinate_app/hallucinate_app/node/views/test_interface.html"
HALLUCINATE_APP_TIME_SERIES_SCHEMA = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql"
)
HALLUCINATE_APP_BENCHMARK_SCHEMA_SCRIPT = (
    "hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py"
)
MOBILE_DESCRIPTOR_MODULE = "mobile/src/orb/metaGlassesOrbDescriptors.js"
MOBILE_ORB_BRIDGE_MODULE = "mobile/src/orb/metaGlassesMobileOrbBridge.js"

REQUIRED_MOBILE_ORB_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)

REQUIRED_ARTIFACT_REFS = (
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
)

REQUIRED_RECEIPT_TABLE = "hallucinate_app_mobile_interop_receipts"


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the hallucinate_app/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileContract:
    """Static contract discovered from Hallucinate App and mobile source files."""

    repo_root: str
    goal_id: str
    task_id: str
    interface_contract: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    mobile_descriptor_module_path: str
    mobile_orb_bridge_module_path: str
    routes: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    receipt_table: str
    exported_symbols: tuple[str, ...]


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one Hallucinate App search routed to mobile."""

    contract_id: str
    interface_contract: str
    goal_id: str
    task_id: str
    source_surface: str
    target_surface: str
    route: str
    operation: str
    query: str
    result_target: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    artifact_refs: tuple[str, ...]
    receipt_table: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    repo_root: str | Path,
) -> HallucinateAppMobileContract:
    """Discover and validate the Hallucinate App/mobile interop contract."""

    root = Path(repo_root)
    if not root.exists():
        raise HallucinateAppMobileInteropError(f"repository root not found: {root}")

    paths = {
        "search_interface": root / HALLUCINATE_APP_SEARCH_INTERFACE,
        "test_interface": root / HALLUCINATE_APP_TEST_INTERFACE,
        "time_series_schema": root / HALLUCINATE_APP_TIME_SERIES_SCHEMA,
        "benchmark_schema_script": root / HALLUCINATE_APP_BENCHMARK_SCHEMA_SCRIPT,
        "mobile_descriptor": root / MOBILE_DESCRIPTOR_MODULE,
        "mobile_orb_bridge": root / MOBILE_ORB_BRIDGE_MODULE,
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app/mobile interop files missing: {missing}"
        )

    search_source = paths["search_interface"].read_text(encoding="utf-8")
    _require_terms(
        search_source,
        (
            "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "buildHallucinateAppMobileSearchHandoff",
            "hallucinate_app-mobile:handoff",
            INTERFACE_CONTRACT,
        ),
        HALLUCINATE_APP_SEARCH_INTERFACE,
    )

    test_interface_source = paths["test_interface"].read_text(encoding="utf-8")
    _require_terms(
        test_interface_source,
        (INTERFACE_CONTRACT, "mobileInteropContract", "mobileInteropResults"),
        HALLUCINATE_APP_TEST_INTERFACE,
    )
    for route in REQUIRED_MOBILE_ORB_ROUTES:
        if route not in test_interface_source:
            raise HallucinateAppMobileInteropError(
                f"{HALLUCINATE_APP_TEST_INTERFACE} is missing route {route}"
            )

    schema_source = paths["time_series_schema"].read_text(encoding="utf-8")
    _require_terms(
        schema_source,
        (REQUIRED_RECEIPT_TABLE, INTERFACE_CONTRACT, "CREATE INDEX"),
        HALLUCINATE_APP_TIME_SERIES_SCHEMA,
    )

    script_source = paths["benchmark_schema_script"].read_text(encoding="utf-8")
    _require_terms(
        script_source,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID",
            "HALLUCINATE_APP_MOBILE_INTEROP_TABLE",
            "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES",
            REQUIRED_RECEIPT_TABLE,
            INTERFACE_CONTRACT,
        ),
        HALLUCINATE_APP_BENCHMARK_SCHEMA_SCRIPT,
    )

    mobile_descriptor_source = paths["mobile_descriptor"].read_text(encoding="utf-8")
    exported_symbols = tuple(
        sorted(set(re.findall(r"export const\s+(HALLUCINATE_APP_MOBILE_[A-Za-z0-9_]+)", mobile_descriptor_source)))
    )
    _require_terms(
        mobile_descriptor_source,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            INTERFACE_CONTRACT,
            TASK_ID,
            GOAL_ID,
        ),
        MOBILE_DESCRIPTOR_MODULE,
    )

    bridge_source = paths["mobile_orb_bridge"].read_text(encoding="utf-8")
    _require_terms(
        bridge_source,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            "register_edge_capabilities",
        ),
        MOBILE_ORB_BRIDGE_MODULE,
    )

    return HallucinateAppMobileContract(
        repo_root=str(root),
        goal_id=GOAL_ID,
        task_id=TASK_ID,
        interface_contract=INTERFACE_CONTRACT,
        search_interface_path=str(paths["search_interface"]),
        test_interface_path=str(paths["test_interface"]),
        time_series_schema_path=str(paths["time_series_schema"]),
        benchmark_schema_script_path=str(paths["benchmark_schema_script"]),
        mobile_descriptor_module_path=str(paths["mobile_descriptor"]),
        mobile_orb_bridge_module_path=str(paths["mobile_orb_bridge"]),
        routes=REQUIRED_MOBILE_ORB_ROUTES,
        artifact_refs=REQUIRED_ARTIFACT_REFS,
        receipt_table=REQUIRED_RECEIPT_TABLE,
        exported_symbols=exported_symbols,
    )


def build_hallucinate_app_mobile_search_handoff(
    repo_root: str | Path,
    *,
    query: str,
    filter: dict[str, Any] | None = None,
    result_target: str = "mobile_card",
) -> HallucinateAppMobileHandoff:
    """Build a content-addressed Hallucinate App search handoff receipt."""

    contract = discover_hallucinate_app_mobile_contract(repo_root)
    payload = {
        "contract_id": contract.interface_contract,
        "source_surface": "hallucinate_app",
        "target_surface": "mobile",
        "route": "/v1/mobile/orb/invoke_service",
        "operation": "invoke_service",
        "payload": {
            "intent": "hallucinate_app.content_browser.search",
            "query": query,
            "filter": filter or {},
            "result_target": result_target,
        },
        "artifact_refs": list(contract.artifact_refs),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id="handsfree.hallucinate-app.mobile@1",
        interface_contract=contract.interface_contract,
        goal_id=contract.goal_id,
        task_id=contract.task_id,
        source_surface="hallucinate_app",
        target_surface="mobile",
        route="/v1/mobile/orb/invoke_service",
        operation="invoke_service",
        query=query,
        result_target=result_target,
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        artifact_refs=contract.artifact_refs,
        receipt_table=contract.receipt_table,
    )


def _require_terms(source: str, terms: tuple[str, ...], label: str) -> None:
    missing = [term for term in terms if term not in source]
    if missing:
        raise HallucinateAppMobileInteropError(f"{label} is missing terms: {missing}")
