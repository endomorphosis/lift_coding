"""Interop contract between SwissKnife and ``external/ipfs_accelerate``.

VAI-662 repairs the VAIOS-G701 objective validation gap that requires
`swissknife` to interoperate with `external/ipfs_accelerate` through
importable contracts, interface descriptors, runtime handoff behavior, and
integration tests. This is part of the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

`external/ipfs_accelerate` ships a DuckDB benchmark/time-series schema
(`data/duckdb/db_schema/time_series_schema.sql`,
`data/duckdb/scripts/create_benchmark_schema.py`,
`data/duckdb/utils/check_database_schema.py`,
`data/duckdb/utils/check_db_schema.py`) that SwissKnife's own benchmark
tooling can consume for performance regression tracking. This module
statically discovers that schema (without importing `external/ipfs_accelerate`
Python -- `create_benchmark_schema.py` is not import-safe in this worktree)
and builds a deterministic ``SwissKnifeIPFSAccelerateHandoff`` receipt that
mirrors the
``swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts``
runtime handoff descriptor on the SwissKnife side.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract swissknife external/ipfs_accelerate"
GOAL_ID = "VAIOS-G701"
GOAL_PACKET = "goal_packet/interoperability/swissknife/06921590135c"
GOAL_PACKET_GOALS = (
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
)

#: DuckDB benchmark tables that the time-series schema extension is expected
#: to define. These are the tables the SwissKnife benchmark surface can query.
REQUIRED_TIME_SERIES_TABLES = (
    "performance_baselines",
    "performance_regressions",
    "performance_trends",
    "regression_notifications",
)

#: SwissKnife-side MCP-IDL operations the handoff must support; kept in sync
#: with ``IPFS_ACCELERATE_DUCKDB_INTEROP_OPERATIONS`` in
#: ``swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts``.
REQUIRED_SWISSKNIFE_DUCKDB_OPERATIONS = (
    "accelerate.duckdb.check_schema",
    "accelerate.duckdb.get_all_tables",
    "accelerate.duckdb.get_performance_results",
    "accelerate.duckdb.create_performance_tables",
    "accelerate.duckdb.create_common_tables",
    "accelerate.duckdb.create_views",
)


class SwissKnifeIPFSAccelerateInteropError(RuntimeError):
    """Raised when either side of the swissknife/ipfs_accelerate contract is missing."""


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
class SwissKnifeIPFSAccelerateHandoff:
    """Deterministic receipt for one benchmark-schema handoff routed to SwissKnife."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    goal_packet: str
    capability: str
    route: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    time_series_tables: tuple[str, ...]
    required_swissknife_operations: tuple[str, ...]
    benchmark_schema_functions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_ipfs_accelerate_duckdb_contract(
    root: str | Path,
) -> IPFSAccelerateDuckDBContract:
    """Discover the DuckDB benchmark/time-series schema contract.

    Reads (without importing) the four DuckDB schema descriptors that
    `external/ipfs_accelerate` ships so SwissKnife can rely on a stable,
    statically-verifiable contract:

    - ``data/duckdb/db_schema/time_series_schema.sql``
    - ``data/duckdb/scripts/create_benchmark_schema.py``
    - ``data/duckdb/utils/check_database_schema.py``
    - ``data/duckdb/utils/check_db_schema.py``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise SwissKnifeIPFSAccelerateInteropError(f"ipfs_accelerate root not found: {root_path}")

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
        raise SwissKnifeIPFSAccelerateInteropError(
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
        raise SwissKnifeIPFSAccelerateInteropError(
            f"ipfs_accelerate time-series schema is missing required tables: {sorted(missing_tables)}"
        )

    benchmark_schema_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    benchmark_schema_functions = tuple(
        sorted(set(re.findall(r"^def\s+([A-Za-z0-9_]+)\s*\(", benchmark_schema_source, flags=re.MULTILINE)))
    )
    required_benchmark_schema_functions = {
        "create_performance_tables",
        "create_common_tables",
        "create_views",
    }
    missing_benchmark_schema_functions = required_benchmark_schema_functions - set(
        benchmark_schema_functions
    )
    if missing_benchmark_schema_functions:
        raise SwissKnifeIPFSAccelerateInteropError(
            "ipfs_accelerate create_benchmark_schema.py is missing functions: "
            f"{sorted(missing_benchmark_schema_functions)}"
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
        raise SwissKnifeIPFSAccelerateInteropError(
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


def build_swissknife_duckdb_handoff(
    ipfs_accelerate_root: str | Path,
    *,
    capability: str = "accelerate.duckdb.benchmark_schema",
    payload: bytes | str | dict[str, Any] | None = None,
) -> SwissKnifeIPFSAccelerateHandoff:
    """Build a deterministic ``external/ipfs_accelerate`` to SwissKnife handoff receipt."""
    contract = discover_ipfs_accelerate_duckdb_contract(ipfs_accelerate_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "swissknife",
            "target": "external/ipfs_accelerate",
            "capability": capability,
            "route": "swissknife-ipfs-accelerate-duckdb-benchmark-schema",
            "time_series_tables": list(contract.time_series_tables),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return SwissKnifeIPFSAccelerateHandoff(
        contract_id="swissknife.ipfs-accelerate-duckdb-interop@1",
        source_repository="swissknife",
        target_repository="external/ipfs_accelerate",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        capability=capability,
        route="swissknife-ipfs-accelerate-duckdb-benchmark-schema",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        time_series_tables=contract.time_series_tables,
        required_swissknife_operations=REQUIRED_SWISSKNIFE_DUCKDB_OPERATIONS,
        benchmark_schema_functions=contract.benchmark_schema_functions,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
