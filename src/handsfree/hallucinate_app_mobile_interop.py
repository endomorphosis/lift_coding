"""Interop contract between ``hallucinate_app`` and ``mobile``.

HAO-740 (attempt 3) repairs the VAIOS-G707 objective validation gap that
requires `hallucinate_app` to interoperate with `mobile` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests.

`hallucinate_app` is a JavaScript/Electron desktop application shipped as a
git submodule, so it cannot be imported directly by the Python-only mobile
Handsfree backend. This module statically discovers (without executing any
Node.js code) the ``interface contract hallucinate_app mobile`` descriptors
that `hallucinate_app` ships:

- ``hallucinate_app/node/dashboard/content_browser/search_interface.js``
  exports ``HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`` and
  ``buildHallucinateAppMobileSearchHandoff()``, normalizing a desktop content
  search into an ``invoke_service`` payload for the mobile ORB bridge.
- ``hallucinate_app/node/views/test_interface.html`` embeds a machine-readable
  fixture of the interface descriptor (contract id, routes, and required
  artifacts) inside the Electron testing dashboard for manual/automated
  runtime probes.
- ``ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`` defines
  the ``hallucinate_app_mobile_interop_receipts`` DuckDB table that records
  every control-surface receipt exchanged during a handoff.
- ``ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`` mirrors
  the same contract id and routes as importable Python literals so a
  benchmark schema build can identify and populate interop receipt evidence.

This module builds a deterministic ``HallucinateAppMobileHandoff`` receipt
that mirrors the mobile ORB bridge's
``HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR``
(``mobile/src/orb/metaGlassesOrbDescriptors.js``), so both sides of the
`hallucinate_app` <-> `mobile` interoperability contract can be verified
statically and exercised at runtime without requiring a live Electron process
or a live mobile client.
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

#: Mobile ORB bridge routes that the hallucinate_app <-> mobile handoff must
#: support, as advertised by the desktop testing dashboard fixture.
REQUIRED_ROUTES = (
    "/v1/mobile/orb/register_edge_capabilities",
    "/v1/mobile/orb/invoke_service",
    "/v1/mobile/orb/dispatch_glasses_response",
    "/v1/mobile/orb/diagnostics",
)

#: Control-surface artifacts that must accompany every handoff receipt.
REQUIRED_ARTIFACTS = (
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
)

#: DuckDB table that records hallucinate_app <-> mobile interop receipts.
INTEROP_RECEIPTS_TABLE = "hallucinate_app_mobile_interop_receipts"


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the hallucinate_app/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileContract:
    """Static hallucinate_app <-> mobile interop contract discovered on disk."""

    root: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    contract_id: str
    required_routes: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    interop_receipts_table: str


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one hallucinate_app -> mobile handoff."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    capability: str
    route: str
    operation: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    required_routes: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    interop_receipts_table: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    root: str | Path,
) -> HallucinateAppMobileContract:
    """Discover the hallucinate_app <-> mobile interop contract.

    Reads (without executing) the four descriptors that `hallucinate_app`
    ships for this contract:

    - ``hallucinate_app/node/dashboard/content_browser/search_interface.js``
    - ``hallucinate_app/node/views/test_interface.html``
    - ``ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql``
    - ``ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py``

    ``root`` should point at the `hallucinate_app` submodule checkout (the
    directory containing both the `hallucinate_app` Electron app and the
    nested `ipfs_accelerate_py` submodule).
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
            f"hallucinate_app mobile interop descriptors missing: {missing}"
        )

    search_interface_source = search_interface_path.read_text(encoding="utf-8")
    contract_id_match = re.search(r"contract_id:\s*'([^']+)'", search_interface_source)
    if not contract_id_match or contract_id_match.group(1) != INTERFACE_CONTRACT:
        raise HallucinateAppMobileInteropError(
            "hallucinate_app search_interface.js is missing the "
            f"{INTERFACE_CONTRACT!r} contract_id"
        )

    test_interface_source = test_interface_path.read_text(encoding="utf-8")
    if INTERFACE_CONTRACT not in test_interface_source:
        raise HallucinateAppMobileInteropError(
            "hallucinate_app test_interface.html is missing the "
            f"{INTERFACE_CONTRACT!r} descriptor fixture"
        )
    discovered_routes = tuple(
        sorted(set(re.findall(r"/v1/mobile/orb/[A-Za-z_]+", test_interface_source)))
    )
    missing_routes = set(REQUIRED_ROUTES) - set(discovered_routes)
    if missing_routes:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app test_interface.html is missing required routes: {sorted(missing_routes)}"
        )

    time_series_schema_sql = time_series_schema_path.read_text(encoding="utf-8")
    if INTEROP_RECEIPTS_TABLE not in time_series_schema_sql:
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app time_series_schema.sql is missing the {INTEROP_RECEIPTS_TABLE!r} table"
        )

    benchmark_schema_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    if INTERFACE_CONTRACT not in benchmark_schema_source:
        raise HallucinateAppMobileInteropError(
            "hallucinate_app create_benchmark_schema.py is missing the "
            f"{INTERFACE_CONTRACT!r} interop evidence block"
        )

    return HallucinateAppMobileContract(
        root=str(root_path),
        search_interface_path=str(search_interface_path),
        test_interface_path=str(test_interface_path),
        time_series_schema_path=str(time_series_schema_path),
        benchmark_schema_script_path=str(benchmark_schema_script_path),
        contract_id=contract_id_match.group(1),
        required_routes=discovered_routes,
        required_artifacts=REQUIRED_ARTIFACTS,
        interop_receipts_table=INTEROP_RECEIPTS_TABLE,
    )


def build_hallucinate_app_mobile_search_handoff(
    hallucinate_app_root: str | Path,
    *,
    capability: str = "content_browser.search_handoff",
    payload: bytes | str | dict[str, Any] | None = None,
) -> HallucinateAppMobileHandoff:
    """Build a deterministic hallucinate_app -> mobile search handoff receipt."""
    contract = discover_hallucinate_app_mobile_contract(hallucinate_app_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "hallucinate_app",
            "target": "mobile",
            "capability": capability,
            "route": "hallucinate-app-search-to-mobile-orb",
            "required_routes": list(contract.required_routes),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id=contract.contract_id,
        source_repository="hallucinate_app",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        capability=capability,
        route="/v1/mobile/orb/invoke_service",
        operation="invoke_service",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        required_routes=contract.required_routes,
        required_artifacts=contract.required_artifacts,
        interop_receipts_table=contract.interop_receipts_table,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
