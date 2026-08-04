"""Interop contract between ``hallucinate_app`` and the ``mobile`` client.

VAI-684 repairs the VAI-671/VAI-674/VAIOS-G707 objective validation gap that
requires `hallucinate_app` to interoperate with `mobile` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests.

`hallucinate_app` is a vendored submodule product surface (not a Python
package this repository imports), so this module statically discovers its
desktop search-to-mobile handoff contract -- the
``HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`` exported by
``hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js``,
the machine-readable fixture embedded in
``hallucinate_app/hallucinate_app/node/views/test_interface.html``, and the
``hallucinate_app_mobile_interop_receipts`` DuckDB table defined by
``hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql``
-- without executing any JavaScript or importing the (partially corrupted,
legacy) ``create_benchmark_schema.py`` script. It then builds a deterministic
receipt describing the handoff so the mobile ORB bridge
(``mobile/src/orb/metaGlassesOrbDescriptors.js``) can route
`interface contract hallucinate_app mobile` traffic through the existing
`/v1/mobile/orb/*` routes.
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

#: Mobile ORB bridge routes the Hallucinate App desktop search surface may
#: hand a request off to.
REQUIRED_MOBILE_ORB_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)

#: Control-surface artifacts required to accompany every handoff.
REQUIRED_HANDOFF_ARTIFACTS = (
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
)

#: DuckDB receipt table the search-to-mobile handoff is recorded into.
REQUIRED_RECEIPT_TABLE = "hallucinate_app_mobile_interop_receipts"


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the hallucinate_app/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppSearchContract:
    """Static contract discovered from the Hallucinate App search surface."""

    root: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    contract_id: str
    source_surface: str
    target_surface: str
    control_surface_contract_ref: str
    route: str
    operation: str
    required_artifacts: tuple[str, ...]
    receipt_table: str


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one search query routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    route: str
    operation: str
    query: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    required_artifacts: tuple[str, ...]
    receipt_table: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def _extract_js_string(source: str, key: str) -> str | None:
    match = re.search(rf"{re.escape(key)}\s*:\s*'([^']*)'", source)
    if match:
        return match.group(1)
    match = re.search(rf'{re.escape(key)}\s*:\s*"([^"]*)"', source)
    return match.group(1) if match else None


def _extract_js_string_array(source: str, key: str) -> tuple[str, ...]:
    match = re.search(rf"{re.escape(key)}\s*:\s*\[([^\]]*)\]", source)
    if not match:
        return ()
    items = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
    return tuple(items)


def discover_hallucinate_app_search_contract(
    root: str | Path,
) -> HallucinateAppSearchContract:
    """Discover the Hallucinate App to mobile search handoff contract.

    Reads (without executing) the JavaScript contract exported by
    ``search_interface.js``, cross-checks the machine-readable fixture in
    ``test_interface.html``, and confirms the DuckDB receipt table declared
    in ``time_series_schema.sql`` -- the three interface descriptors that
    make up `interface contract hallucinate_app mobile`.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise HallucinateAppMobileInteropError(f"hallucinate_app root not found: {root_path}")

    search_interface_path = (
        root_path
        / "hallucinate_app"
        / "node"
        / "dashboard"
        / "content_browser"
        / "search_interface.js"
    )
    test_interface_path = root_path / "hallucinate_app" / "node" / "views" / "test_interface.html"
    time_series_schema_path = (
        root_path
        / "ipfs_accelerate_py"
        / "data"
        / "duckdb"
        / "db_schema"
        / "time_series_schema.sql"
    )

    missing = [
        str(path)
        for path in (search_interface_path, test_interface_path, time_series_schema_path)
        if not path.exists()
    ]
    if missing:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app mobile interop descriptors missing: {missing}"
        )

    search_source = search_interface_path.read_text(encoding="utf-8")
    if "HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT" not in search_source:
        raise HallucinateAppMobileInteropError(
            "search_interface.js is missing HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT"
        )

    contract_id = _extract_js_string(search_source, "contract_id")
    source_surface = _extract_js_string(search_source, "source_surface")
    target_surface = _extract_js_string(search_source, "target_surface")
    control_surface_contract_ref = _extract_js_string(search_source, "control_surface_contract_ref")
    route = _extract_js_string(search_source, "route")
    operation = _extract_js_string(search_source, "operation")
    required_artifacts = _extract_js_string_array(search_source, "required_artifacts")

    if contract_id != INTERFACE_CONTRACT:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js contract_id mismatch: {contract_id!r} != {INTERFACE_CONTRACT!r}"
        )
    if source_surface != "hallucinate_app" or target_surface != "mobile":
        raise HallucinateAppMobileInteropError(
            "search_interface.js contract must route hallucinate_app -> mobile"
        )
    missing_artifacts = set(REQUIRED_HANDOFF_ARTIFACTS) - set(required_artifacts)
    if missing_artifacts:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js contract is missing required artifacts: {sorted(missing_artifacts)}"
        )

    test_interface_source = test_interface_path.read_text(encoding="utf-8")
    if INTERFACE_CONTRACT not in test_interface_source:
        raise HallucinateAppMobileInteropError(
            "test_interface.html is missing the hallucinate_app mobile interop fixture"
        )

    schema_sql = time_series_schema_path.read_text(encoding="utf-8")
    discovered_tables = set(
        re.findall(
            r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([A-Za-z0-9_]+)",
            schema_sql,
            flags=re.IGNORECASE,
        )
    )
    if REQUIRED_RECEIPT_TABLE not in discovered_tables:
        raise HallucinateAppMobileInteropError(
            f"time_series_schema.sql is missing required table: {REQUIRED_RECEIPT_TABLE}"
        )

    return HallucinateAppSearchContract(
        root=str(root_path),
        search_interface_path=str(search_interface_path),
        test_interface_path=str(test_interface_path),
        time_series_schema_path=str(time_series_schema_path),
        contract_id=contract_id,
        source_surface=source_surface,
        target_surface=target_surface,
        control_surface_contract_ref=control_surface_contract_ref or "",
        route=route or REQUIRED_MOBILE_ORB_ROUTES[1],
        operation=operation or "invoke_service",
        required_artifacts=tuple(required_artifacts),
        receipt_table=REQUIRED_RECEIPT_TABLE,
    )


def build_mobile_search_handoff(
    hallucinate_app_root: str | Path,
    query: str = "",
    *,
    payload: bytes | str | dict[str, Any] | None = None,
) -> HallucinateAppMobileHandoff:
    """Build a deterministic ``hallucinate_app`` to mobile search handoff receipt."""
    contract = discover_hallucinate_app_search_contract(hallucinate_app_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": contract.source_surface,
            "target": contract.target_surface,
            "contract_id": contract.contract_id,
            "route": contract.route,
            "operation": contract.operation,
            "query": query,
            "required_artifacts": list(contract.required_artifacts),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id=contract.contract_id,
        source_repository=contract.source_surface,
        target_repository=contract.target_surface,
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        route=contract.route,
        operation=contract.operation,
        query=query,
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        required_artifacts=contract.required_artifacts,
        receipt_table=contract.receipt_table,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
