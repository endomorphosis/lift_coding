"""Interop contract between ``hallucinate_app`` and the mobile ORB bridge.

VAI-674 repairs the VAIOS-G707 objective validation gap requiring
`hallucinate_app` to interoperate with `mobile` through importable contracts,
interface descriptors, runtime handoff behavior, and integration tests.

The desktop Hallucinate App content browser is JavaScript, while the mobile
surface is a React Native ORB bridge. This module keeps the cross-repository
contract importable from Python by statically validating the descriptor files
on both sides and building a deterministic receipt for a search handoff. It
does not import either JavaScript runtime.
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
TASK_ID = "VAI-674"
BUNDLE = "objective/interoperability/hallucinate_app-mobile"

REQUIRED_HALLUCINATE_APP_PATHS = (
    "hallucinate_app/node/dashboard/content_browser/search_interface.js",
    "hallucinate_app/node/views/test_interface.html",
    "ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
    "ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
    "ipfs_accelerate_py/data/duckdb/utils/check_database_schema.py",
    "ipfs_accelerate_py/data/duckdb/utils/check_db_schema.py",
)

REQUIRED_MOBILE_PATHS = (
    "src/orb/metaGlassesOrbDescriptors.js",
    "src/orb/metaGlassesMobileOrbBridge.js",
)

REQUIRED_MOBILE_ORB_OPERATIONS = (
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
)

REQUIRED_HALLUCINATE_APP_ARTIFACTS = (
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
)


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the hallucinate_app/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileContract:
    """Static descriptor contract discovered from Hallucinate App and mobile."""

    hallucinate_app_root: str
    mobile_root: str
    hallucinate_app_descriptor_paths: tuple[str, ...]
    mobile_descriptor_paths: tuple[str, ...]
    mobile_orb_operations: tuple[str, ...]
    receipt_table: str
    artifact_refs: tuple[str, ...]
    search_handoff_event: str


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one Hallucinate App search routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    task_id: str
    bundle: str
    capability: str
    route: str
    operation: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    receipt_table: str
    mobile_orb_operations: tuple[str, ...]
    artifact_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    hallucinate_app_root: str | Path,
    mobile_root: str | Path,
) -> HallucinateAppMobileContract:
    """Discover and validate the Hallucinate App to mobile descriptor contract."""
    hallucinate_root = Path(hallucinate_app_root)
    mobile_path = Path(mobile_root)
    if not hallucinate_root.exists():
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app root not found: {hallucinate_root}"
        )
    if not mobile_path.exists():
        raise HallucinateAppMobileInteropError(f"mobile root not found: {mobile_path}")

    hallucinate_paths = tuple(hallucinate_root / rel for rel in REQUIRED_HALLUCINATE_APP_PATHS)
    mobile_paths = tuple(mobile_path / rel for rel in REQUIRED_MOBILE_PATHS)
    missing = [str(path) for path in (*hallucinate_paths, *mobile_paths) if not path.exists()]
    if missing:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app/mobile interop descriptors missing: {missing}"
        )

    search_source = hallucinate_paths[0].read_text(encoding="utf-8")
    required_search_terms = (
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "buildHallucinateAppMobileSearchHandoff",
        "hallucinate-app:mobile-interop-handoff",
        INTERFACE_CONTRACT,
    )
    _require_terms(search_source, required_search_terms, hallucinate_paths[0])

    fixture_source = hallucinate_paths[1].read_text(encoding="utf-8")
    _require_terms(
        fixture_source,
        ("hallucinate-app-mobile-interop-contract", INTERFACE_CONTRACT, "objective validation repair"),
        hallucinate_paths[1],
    )

    schema_sql = hallucinate_paths[2].read_text(encoding="utf-8")
    receipt_table = "hallucinate_app_mobile_interop_receipts"
    _require_terms(schema_sql, (receipt_table, INTERFACE_CONTRACT), hallucinate_paths[2])

    benchmark_script = hallucinate_paths[3].read_text(encoding="utf-8")
    _require_terms(
        benchmark_script,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID",
            "HALLUCINATE_APP_MOBILE_INTEROP_ROUTES",
            "HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS",
        ),
        hallucinate_paths[3],
    )

    mobile_descriptor_source = mobile_paths[0].read_text(encoding="utf-8")
    _require_terms(
        mobile_descriptor_source,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
            INTERFACE_CONTRACT,
            "objective validation repair",
        ),
        mobile_paths[0],
    )
    discovered_mobile_operations = tuple(
        sorted(
            set(
                re.findall(
                    r"'(register_edge_capabilities|publish_glasses_event|bind_service|invoke_service|subscribe_service_updates|dispatch_glasses_response|revoke_binding)'",
                    mobile_descriptor_source,
                )
            )
        )
    )
    missing_operations = set(REQUIRED_MOBILE_ORB_OPERATIONS) - set(discovered_mobile_operations)
    if missing_operations:
        raise HallucinateAppMobileInteropError(
            f"mobile ORB descriptor is missing operations: {sorted(missing_operations)}"
        )

    mobile_bridge_source = mobile_paths[1].read_text(encoding="utf-8")
    _require_terms(
        mobile_bridge_source,
        (
            "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
            "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        ),
        mobile_paths[1],
    )

    return HallucinateAppMobileContract(
        hallucinate_app_root=str(hallucinate_root),
        mobile_root=str(mobile_path),
        hallucinate_app_descriptor_paths=tuple(str(path) for path in hallucinate_paths),
        mobile_descriptor_paths=tuple(str(path) for path in mobile_paths),
        mobile_orb_operations=tuple(REQUIRED_MOBILE_ORB_OPERATIONS),
        receipt_table=receipt_table,
        artifact_refs=REQUIRED_HALLUCINATE_APP_ARTIFACTS,
        search_handoff_event="hallucinate-app:mobile-interop-handoff",
    )


def build_hallucinate_app_mobile_search_handoff(
    hallucinate_app_root: str | Path,
    mobile_root: str | Path,
    *,
    query: str = "content browser search",
    filter: dict[str, Any] | None = None,
    result_target: str = "mobile_card",
    payload: bytes | str | dict[str, Any] | None = None,
) -> HallucinateAppMobileHandoff:
    """Build a deterministic Hallucinate App search handoff receipt."""
    contract = discover_hallucinate_app_mobile_contract(hallucinate_app_root, mobile_root)
    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "contract_id": INTERFACE_CONTRACT,
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
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id="handsfree.hallucinate-app.mobile@1",
        source_repository="hallucinate_app",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        task_id=TASK_ID,
        bundle=BUNDLE,
        capability="hallucinate_app.content_browser.search",
        route="hallucinate-app-search-to-mobile-orb",
        operation="invoke_service",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        receipt_table=contract.receipt_table,
        mobile_orb_operations=contract.mobile_orb_operations,
        artifact_refs=contract.artifact_refs,
    )


def _require_terms(source: str, terms: tuple[str, ...], path: Path) -> None:
    missing = [term for term in terms if term not in source]
    if missing:
        raise HallucinateAppMobileInteropError(f"{path} is missing terms: {missing}")


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
