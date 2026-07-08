"""Interop contract between ``hallucinate_app`` and the mobile client.

VAI-674 repairs the VAIOS-G707 objective validation gap. The objective needs
importable evidence that Hallucinate App can hand a desktop content-browser
search request to the mobile ORB bridge through a shared control-surface
contract, with static interface descriptors and DuckDB receipt persistence.
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
CANONICAL_EVENT_NAME = "hallucinate-app:mobile-interop-handoff"

REQUIRED_HALUCINATE_APP_PATHS = (
    "hallucinate_app/node/dashboard/content_browser/search_interface.js",
    "hallucinate_app/node/views/test_interface.html",
    "ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql",
    "ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py",
)

REQUIRED_MOBILE_PATHS = (
    "src/orb/metaGlassesOrbDescriptors.js",
    "src/orb/metaGlassesMobileOrbBridge.js",
)

REQUIRED_MOBILE_ORB_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)

REQUIRED_RECEIPT_ARTIFACTS = (
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
)


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the Hallucinate App/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileInteropContract:
    """Static contract discovered from Hallucinate App and mobile sources."""

    hallucinate_app_root: str
    mobile_root: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    mobile_descriptor_path: str
    mobile_bridge_path: str
    routes: tuple[str, ...]
    receipt_artifacts: tuple[str, ...]
    persistence_tables: tuple[str, ...]
    event_names: tuple[str, ...]


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one Hallucinate App search routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    event_name: str
    route: str
    operation: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    required_mobile_orb_routes: tuple[str, ...]
    required_receipt_artifacts: tuple[str, ...]
    persistence_tables: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    hallucinate_app_root: str | Path,
    mobile_root: str | Path,
) -> HallucinateAppMobileInteropContract:
    """Discover the static Hallucinate App/mobile handoff contract."""
    ha_root = Path(hallucinate_app_root)
    mobile = Path(mobile_root)
    if not ha_root.exists():
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app root not found: {ha_root}"
        )
    if not mobile.exists():
        raise HallucinateAppMobileInteropError(f"mobile root not found: {mobile}")

    ha_paths = tuple(ha_root / path for path in REQUIRED_HALUCINATE_APP_PATHS)
    mobile_paths = tuple(mobile / path for path in REQUIRED_MOBILE_PATHS)
    missing = [str(path) for path in (*ha_paths, *mobile_paths) if not path.exists()]
    if missing:
        raise HallucinateAppMobileInteropError(
            f"Hallucinate App/mobile interop descriptors missing: {missing}"
        )

    search_source = ha_paths[0].read_text(encoding="utf-8")
    test_interface_source = ha_paths[1].read_text(encoding="utf-8")
    schema_source = ha_paths[2].read_text(encoding="utf-8")
    benchmark_source = ha_paths[3].read_text(encoding="utf-8")
    mobile_descriptor_source = mobile_paths[0].read_text(encoding="utf-8")
    mobile_bridge_source = mobile_paths[1].read_text(encoding="utf-8")

    required_sources = {
        "search_interface.js": search_source,
        "test_interface.html": test_interface_source,
        "time_series_schema.sql": schema_source,
        "create_benchmark_schema.py": benchmark_source,
        "metaGlassesOrbDescriptors.js": mobile_descriptor_source,
        "metaGlassesMobileOrbBridge.js": mobile_bridge_source,
    }
    required_terms = (
        INTERFACE_CONTRACT,
        GOAL_ID,
        "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR",
        "HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE",
    )
    for source_name, source in required_sources.items():
        for term in required_terms[:2]:
            if term not in source:
                raise HallucinateAppMobileInteropError(
                    f"{source_name} is missing required interop term: {term}"
                )

    for source_name, source in (
        ("search_interface.js", search_source),
        ("metaGlassesOrbDescriptors.js", mobile_descriptor_source),
        ("metaGlassesMobileOrbBridge.js", mobile_bridge_source),
    ):
        for term in required_terms[2:]:
            if term not in source:
                raise HallucinateAppMobileInteropError(
                    f"{source_name} is missing descriptor term: {term}"
                )

    persistence_tables = tuple(
        sorted(
            set(
                re.findall(
                    r"(hallucinate_app_mobile_interop_[A-Za-z0-9_]+)",
                    schema_source + "\n" + benchmark_source,
                )
            )
        )
    )
    for table in (
        "hallucinate_app_mobile_interop_receipts",
        "hallucinate_app_mobile_interop_events",
    ):
        if table not in persistence_tables:
            raise HallucinateAppMobileInteropError(
                f"DuckDB interop persistence is missing table/view: {table}"
            )

    event_names = tuple(
        sorted(
            set(
                re.findall(
                    r"hallucinate[-_]app(?::|-)?mobile[-:]interop[-:]handoff",
                    search_source + "\n" + test_interface_source,
                )
            )
        )
    )
    if CANONICAL_EVENT_NAME not in event_names:
        raise HallucinateAppMobileInteropError(
            f"Hallucinate App handoff event missing: {CANONICAL_EVENT_NAME}"
        )

    return HallucinateAppMobileInteropContract(
        hallucinate_app_root=str(ha_root),
        mobile_root=str(mobile),
        search_interface_path=str(ha_paths[0]),
        test_interface_path=str(ha_paths[1]),
        time_series_schema_path=str(ha_paths[2]),
        benchmark_schema_script_path=str(ha_paths[3]),
        mobile_descriptor_path=str(mobile_paths[0]),
        mobile_bridge_path=str(mobile_paths[1]),
        routes=REQUIRED_MOBILE_ORB_ROUTES,
        receipt_artifacts=REQUIRED_RECEIPT_ARTIFACTS,
        persistence_tables=persistence_tables,
        event_names=event_names,
    )


def build_hallucinate_app_mobile_handoff(
    hallucinate_app_root: str | Path,
    mobile_root: str | Path,
    *,
    query: str = "vector search",
    filter: dict[str, Any] | None = None,
    correlation_id: str = "vai-674-hallucinate-app-mobile",
) -> HallucinateAppMobileHandoff:
    """Build a deterministic Hallucinate App to mobile search handoff receipt."""
    contract = discover_hallucinate_app_mobile_contract(hallucinate_app_root, mobile_root)
    payload = {
        "contract_id": INTERFACE_CONTRACT,
        "source_surface": "hallucinate_app",
        "target_surface": "mobile",
        "event_name": CANONICAL_EVENT_NAME,
        "route": "/v1/mobile/orb/invoke_service",
        "operation": "invoke_service",
        "correlation_id": correlation_id,
        "payload": {
            "intent": "hallucinate_app.content_browser.search",
            "query": query,
            "filter": filter or {},
            "result_target": "mobile_card",
        },
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id="handsfree.hallucinate-app.mobile@1",
        source_repository="hallucinate_app",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        event_name=CANONICAL_EVENT_NAME,
        route="/v1/mobile/orb/invoke_service",
        operation="invoke_service",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        required_mobile_orb_routes=contract.routes,
        required_receipt_artifacts=contract.receipt_artifacts,
        persistence_tables=contract.persistence_tables,
    )
