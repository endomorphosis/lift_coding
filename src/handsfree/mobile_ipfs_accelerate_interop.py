"""Interop contract between the mobile client and ``external/ipfs_accelerate``.

VAI-672 repairs the VAI-661/VAIOS-G719 objective validation gap that requires
`mobile` to interoperate with `external/ipfs_accelerate` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests.

`external/ipfs_accelerate` cannot be imported directly by the mobile React
Native client, so this module normalizes its DuckDB benchmark/time-series
schema descriptors into a small, deterministic runtime contract that the
mobile ORB bridge can route through the existing IPFS descriptor pack. The
contract lets the mobile Handsfree app render accelerate performance
benchmarks (throughput, latency, memory, power, and regression status) inside
a display widget without importing any Python from the submodule.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack_as_dicts

INTERFACE_CONTRACT = "interface contract mobile external/ipfs_accelerate"
GOAL_ID = "VAIOS-G719"

#: DuckDB benchmark tables that the time-series schema extension is expected
#: to define. These are the tables the mobile benchmark widget can query.
REQUIRED_TIME_SERIES_TABLES = (
    "performance_baselines",
    "performance_regressions",
    "performance_trends",
    "regression_notifications",
)

#: Mobile-side benchmark widget actions the handoff must support.
REQUIRED_MOBILE_WIDGET_ACTIONS = (
    "mobile_render_performance_benchmark_widget",
    "mobile_update_performance_benchmark_widget",
    "mobile_clear_performance_benchmark_widget",
    "mobile_refresh_performance_benchmark_metrics",
)


class MobileIPFSAccelerateInteropError(RuntimeError):
    """Raised when either side of the mobile/ipfs_accelerate contract is missing."""


@dataclass(frozen=True)
class IPFSAccelerateDuckDBContract:
    """Static DuckDB benchmark schema contract discovered from the submodule."""

    root: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    check_database_schema_path: str
    check_db_schema_path: str
    time_series_tables: tuple[str, ...]
    benchmark_schema_functions: tuple[str, ...]
    check_schema_functions: tuple[str, ...]


@dataclass(frozen=True)
class MobileIPFSAccelerateHandoff:
    """Deterministic receipt for one benchmark payload routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    capability: str
    route: str
    endpoint_path: str
    method: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    time_series_tables: tuple[str, ...]
    required_mobile_widget_actions: tuple[str, ...]
    benchmark_schema_functions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_ipfs_accelerate_duckdb_contract(
    root: str | Path,
) -> IPFSAccelerateDuckDBContract:
    """Discover the DuckDB benchmark/time-series schema contract.

    Reads (without importing) the four DuckDB schema descriptors that
    `external/ipfs_accelerate` ships so the mobile client can rely on a
    stable, statically-verifiable contract:

    - ``data/duckdb/db_schema/time_series_schema.sql``
    - ``data/duckdb/scripts/create_benchmark_schema.py``
    - ``data/duckdb/utils/check_database_schema.py``
    - ``data/duckdb/utils/check_db_schema.py``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise MobileIPFSAccelerateInteropError(f"ipfs_accelerate root not found: {root_path}")

    time_series_schema_path = root_path / "data" / "duckdb" / "db_schema" / "time_series_schema.sql"
    benchmark_schema_script_path = root_path / "data" / "duckdb" / "scripts" / "create_benchmark_schema.py"
    check_database_schema_path = root_path / "data" / "duckdb" / "utils" / "check_database_schema.py"
    check_db_schema_path = root_path / "data" / "duckdb" / "utils" / "check_db_schema.py"

    missing = [
        str(path)
        for path in (
            time_series_schema_path,
            benchmark_schema_script_path,
            check_database_schema_path,
            check_db_schema_path,
        )
        if not path.exists()
    ]
    if missing:
        raise MobileIPFSAccelerateInteropError(
            f"ipfs_accelerate DuckDB benchmark schema descriptors missing: {missing}"
        )

    schema_sql = time_series_schema_path.read_text(encoding="utf-8")
    discovered_tables = tuple(
        sorted(
            set(
                re.findall(
                    r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([A-Za-z0-9_]+)",
                    schema_sql,
                    flags=re.IGNORECASE,
                )
            )
        )
    )
    missing_tables = set(REQUIRED_TIME_SERIES_TABLES) - set(discovered_tables)
    if missing_tables:
        raise MobileIPFSAccelerateInteropError(
            f"ipfs_accelerate time-series schema is missing required tables: {sorted(missing_tables)}"
        )

    benchmark_schema_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    benchmark_schema_functions = tuple(
        sorted(set(re.findall(r"^def\s+([A-Za-z0-9_]+)\s*\(", benchmark_schema_source, flags=re.MULTILINE)))
    )
    if "create_performance_tables" not in benchmark_schema_functions:
        raise MobileIPFSAccelerateInteropError(
            "ipfs_accelerate create_benchmark_schema.py is missing create_performance_tables()"
        )

    check_database_schema_source = check_database_schema_path.read_text(encoding="utf-8")
    check_db_schema_source = check_db_schema_path.read_text(encoding="utf-8")
    check_schema_functions = tuple(
        sorted(
            set(
                re.findall(r"^def\s+([A-Za-z0-9_]+)\s*\(", check_database_schema_source, flags=re.MULTILINE)
            )
            | set(re.findall(r"^def\s+([A-Za-z0-9_]+)\s*\(", check_db_schema_source, flags=re.MULTILINE))
        )
    )
    required_check_functions = {"check_schema", "get_all_tables", "get_performance_results"}
    missing_check_functions = required_check_functions - set(check_schema_functions)
    if missing_check_functions:
        raise MobileIPFSAccelerateInteropError(
            f"ipfs_accelerate schema-check utilities are missing functions: {sorted(missing_check_functions)}"
        )

    return IPFSAccelerateDuckDBContract(
        root=str(root_path),
        time_series_schema_path=str(time_series_schema_path),
        benchmark_schema_script_path=str(benchmark_schema_script_path),
        check_database_schema_path=str(check_database_schema_path),
        check_db_schema_path=str(check_db_schema_path),
        time_series_tables=discovered_tables,
        benchmark_schema_functions=benchmark_schema_functions,
        check_schema_functions=check_schema_functions,
    )


def build_mobile_benchmark_widget_handoff(
    ipfs_accelerate_root: str | Path,
    *,
    capability: str = "performance.benchmark_widget",
    payload: bytes | str | dict[str, Any] | None = None,
) -> MobileIPFSAccelerateHandoff:
    """Build a deterministic ``external/ipfs_accelerate`` to mobile handoff receipt."""
    contract = discover_ipfs_accelerate_duckdb_contract(ipfs_accelerate_root)

    descriptor = next(
        item
        for item in get_ipfs_descriptor_pack_as_dicts()
        if item["descriptor_id"] == "ipfs.capabilities"
    )

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "external/ipfs_accelerate",
            "target": "mobile",
            "capability": capability,
            "route": "ipfs-accelerate-benchmark-to-mobile-widget",
            "time_series_tables": list(contract.time_series_tables),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return MobileIPFSAccelerateHandoff(
        contract_id="handsfree.mobile.external-ipfs-accelerate@1",
        source_repository="external/ipfs_accelerate",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        capability=capability,
        route="ipfs-accelerate-benchmark-to-mobile-widget",
        endpoint_path=descriptor["endpoint_path"],
        method=descriptor["method"],
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        time_series_tables=contract.time_series_tables,
        required_mobile_widget_actions=REQUIRED_MOBILE_WIDGET_ACTIONS,
        benchmark_schema_functions=contract.benchmark_schema_functions,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
