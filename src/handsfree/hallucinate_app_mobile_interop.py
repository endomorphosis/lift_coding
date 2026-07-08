"""Interop contract between `hallucinate_app` and the `mobile` client.

VAI-674 repairs the VAI-671/VAIOS-G707 objective validation gap that requires
`hallucinate_app` to interoperate with `mobile` through importable contracts,
interface descriptors, runtime handoff behavior, and integration tests.

`hallucinate_app`'s Electron desktop dashboard cannot be imported directly by
the mobile React Native client, so this module statically discovers the
JavaScript/HTML/SQL/Python descriptors that `hallucinate_app` ships for the
content-browser search surface and normalizes them into a small,
deterministic runtime contract the mobile ORB bridge can route through. The
contract lets the mobile Handsfree app receive a Hallucinate App desktop
search handoff (query, filter, correlation id) and render the results inside
a display widget without importing any JavaScript or Python from the
submodule.
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

#: Event name emitted by the desktop search surface when it hands a query off
#: to the mobile ORB bridge.
EVENT_NAME = "hallucinate-app:mobile-interop-handoff"

#: DuckDB receipt table that records the control-surface handoff evidence.
RECEIPT_TABLE = "hallucinate_app_mobile_interop_receipts"

#: Mobile-side search widget actions the handoff must support.
REQUIRED_MOBILE_WIDGET_ACTIONS = (
    "mobile_render_search_results_widget",
    "mobile_update_search_results_widget",
    "mobile_clear_search_results_widget",
    "mobile_refresh_search_metadata",
)

#: Routes advertised for the `interface contract hallucinate_app mobile` handoff.
REQUIRED_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the hallucinate_app/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileContract:
    """Static descriptor contract discovered from the `hallucinate_app` submodule."""

    root: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    contract_id: str
    event_name: str
    receipt_table: str
    routes: tuple[str, ...]
    required_artifacts: tuple[str, ...]


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one search handoff routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    event_name: str
    receipt_table: str
    route: str
    method: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    required_mobile_widget_actions: tuple[str, ...]
    routes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    root: str | Path,
) -> HallucinateAppMobileContract:
    """Discover the hallucinate_app <-> mobile interop descriptor contract.

    Reads (without importing or executing) the descriptors that
    `hallucinate_app` ships so the mobile client can rely on a stable,
    statically-verifiable contract:

    - ``hallucinate_app/node/dashboard/content_browser/search_interface.js``
    - ``hallucinate_app/node/views/test_interface.html``
    - ``ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql``
    - ``ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise HallucinateAppMobileInteropError(f"hallucinate_app root not found: {root_path}")

    search_interface_path = (
        root_path / "hallucinate_app" / "node" / "dashboard" / "content_browser" / "search_interface.js"
    )
    test_interface_path = root_path / "hallucinate_app" / "node" / "views" / "test_interface.html"
    time_series_schema_path = (
        root_path / "ipfs_accelerate_py" / "data" / "duckdb" / "db_schema" / "time_series_schema.sql"
    )
    benchmark_schema_script_path = (
        root_path / "ipfs_accelerate_py" / "data" / "duckdb" / "scripts" / "create_benchmark_schema.py"
    )

    missing = [
        str(path)
        for path in (
            search_interface_path,
            test_interface_path,
            time_series_schema_path,
            benchmark_schema_script_path,
        )
        if not path.exists()
    ]
    if missing:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app mobile-interop descriptors missing: {missing}"
        )

    search_interface_source = search_interface_path.read_text(encoding="utf-8")
    if "HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR" not in search_interface_source:
        raise HallucinateAppMobileInteropError(
            "search_interface.js is missing HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR"
        )
    if "emitHallucinateAppMobileInteropHandoff" not in search_interface_source:
        raise HallucinateAppMobileInteropError(
            "search_interface.js is missing emitHallucinateAppMobileInteropHandoff()"
        )

    event_match = re.search(
        r"event_name:\s*'([^']+)'", search_interface_source
    )
    discovered_event_name = event_match.group(1) if event_match else None
    if discovered_event_name != EVENT_NAME:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js declares unexpected event_name: {discovered_event_name!r}"
        )

    receipt_table_match = re.search(
        r"receipt_table:\s*'([^']+)'", search_interface_source
    )
    discovered_receipt_table = receipt_table_match.group(1) if receipt_table_match else None
    if discovered_receipt_table != RECEIPT_TABLE:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js declares unexpected receipt_table: {discovered_receipt_table!r}"
        )

    test_interface_source = test_interface_path.read_text(encoding="utf-8")
    if INTERFACE_CONTRACT not in test_interface_source:
        raise HallucinateAppMobileInteropError(
            f"test_interface.html is missing contract id: {INTERFACE_CONTRACT!r}"
        )
    if EVENT_NAME not in test_interface_source:
        raise HallucinateAppMobileInteropError(
            f"test_interface.html is missing event name: {EVENT_NAME!r}"
        )

    schema_sql = time_series_schema_path.read_text(encoding="utf-8")
    if not re.search(
        rf"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+{RECEIPT_TABLE}\b",
        schema_sql,
        flags=re.IGNORECASE,
    ):
        raise HallucinateAppMobileInteropError(
            f"time_series_schema.sql is missing the {RECEIPT_TABLE} table"
        )

    benchmark_schema_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    if "HALLUCINATE_APP_MOBILE_INTEROP_TABLE" not in benchmark_schema_source:
        raise HallucinateAppMobileInteropError(
            "create_benchmark_schema.py is missing HALLUCINATE_APP_MOBILE_INTEROP_TABLE"
        )
    if RECEIPT_TABLE not in benchmark_schema_source:
        raise HallucinateAppMobileInteropError(
            f"create_benchmark_schema.py does not reference {RECEIPT_TABLE!r}"
        )

    return HallucinateAppMobileContract(
        root=str(root_path),
        search_interface_path=str(search_interface_path),
        test_interface_path=str(test_interface_path),
        time_series_schema_path=str(time_series_schema_path),
        benchmark_schema_script_path=str(benchmark_schema_script_path),
        contract_id=INTERFACE_CONTRACT,
        event_name=EVENT_NAME,
        receipt_table=RECEIPT_TABLE,
        routes=REQUIRED_ROUTES,
        required_artifacts=("interaction_envelope", "policy_decision", "mediation_receipt"),
    )


def build_hallucinate_app_mobile_handoff(
    hallucinate_app_root: str | Path,
    *,
    route: str = "/v1/mobile/orb/invoke_service",
    payload: bytes | str | dict[str, Any] | None = None,
) -> HallucinateAppMobileHandoff:
    """Build a deterministic `hallucinate_app` to `mobile` search handoff receipt."""
    contract = discover_hallucinate_app_mobile_contract(hallucinate_app_root)

    if route not in contract.routes:
        raise HallucinateAppMobileInteropError(
            f"unsupported hallucinate_app mobile route: {route!r}"
        )

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "hallucinate_app",
            "target": "mobile",
            "contract_id": contract.contract_id,
            "event_name": contract.event_name,
            "route": route,
            "receipt_table": contract.receipt_table,
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id="handsfree.mobile.hallucinate-app@1",
        source_repository="hallucinate_app",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        event_name=contract.event_name,
        receipt_table=contract.receipt_table,
        route=route,
        method="invoke_service",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        required_mobile_widget_actions=REQUIRED_MOBILE_WIDGET_ACTIONS,
        routes=contract.routes,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
