"""Interop contract between Meta Wearables DAT Android and ``external/ipfs_accelerate``.

HAO-737 repairs the VAIOS-G709 objective validation gap for the shared
``goal_packet/interoperability/external/6595cbbfadb9`` packet covering
VAIOS-G709, VAIOS-G710, and VAIOS-G711.

The Android DAT external tree is intentionally treated as a display consumer
contract instead of a Python import root. This module statically validates the
machine-readable DAT Android descriptor and the ``external/ipfs_accelerate``
DuckDB benchmark/time-series descriptors, then builds a deterministic handoff
receipt for benchmark-widget payloads.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_accelerate"
TASK_ID = "HAO-737"
GOAL_ID = "VAIOS-G709"
GOAL_PACKET = "goal_packet/interoperability/external/6595cbbfadb9"
GOAL_PACKET_GOALS = ("VAIOS-G709", "VAIOS-G710", "VAIOS-G711")

REQUIRED_DAT_ANDROID_CONTRACT_PATHS = (
    Path("samples/DisplayAccess/README.md"),
    Path("samples/DisplayAccess/app/build.gradle.kts"),
    Path(
        "samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/"
        "externalsampleapps/displayaccess/display/DisplayViewModel.kt"
    ),
    Path(".cursor/rules/display-access.mdc"),
)

REQUIRED_TIME_SERIES_TABLES = (
    "performance_baselines",
    "performance_regressions",
    "performance_trends",
    "regression_notifications",
)

REQUIRED_BENCHMARK_SCHEMA_FUNCTIONS = (
    "create_performance_tables",
    "create_common_tables",
    "create_views",
)

REQUIRED_CHECK_SCHEMA_FUNCTIONS = (
    "check_schema",
    "get_all_tables",
    "get_performance_results",
)

REQUIRED_DAT_ANDROID_METHODS = (
    "renderPerformanceBenchmarkWidget",
    "updatePerformanceBenchmarkWidget",
    "clearPerformanceBenchmarkWidget",
    "refreshPerformanceBenchmarkMetrics",
)

DAT_ANDROID_TABLE_BY_METHOD = {
    "renderPerformanceBenchmarkWidget": "performance_baselines",
    "updatePerformanceBenchmarkWidget": "performance_trends",
    "clearPerformanceBenchmarkWidget": "regression_notifications",
    "refreshPerformanceBenchmarkMetrics": "performance_regressions",
}


class MetaWearablesDatAndroidIPFSAccelerateInteropError(RuntimeError):
    """Raised when either side of the DAT Android/ipfs_accelerate contract is missing."""


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
class MetaWearablesDatAndroidContract:
    """Static Android DAT display contract used for benchmark-widget handoff."""

    root: str
    descriptor_paths: tuple[str, ...]
    contract_id: str
    interface_contract: str
    task_id: str
    goal_id: str
    goal_packet: str
    goal_packet_goals: tuple[str, ...]
    producer: str
    consumer: str
    dat_display_methods: tuple[str, ...]
    table_by_method: dict[str, str]
    schema_refs: dict[str, str]


@dataclass(frozen=True)
class MetaWearablesDatAndroidIPFSAccelerateHandoff:
    """Deterministic receipt for an accelerate benchmark payload routed to Android DAT."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    task_id: str
    goal_id: str
    goal_packet: str
    goal_packet_goals: tuple[str, ...]
    capability: str
    route: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    time_series_tables: tuple[str, ...]
    dat_display_methods: tuple[str, ...]
    table_by_method: dict[str, str]
    benchmark_schema_functions: tuple[str, ...]
    check_schema_functions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_ipfs_accelerate_duckdb_contract(root: str | Path) -> IPFSAccelerateDuckDBContract:
    """Discover the ``external/ipfs_accelerate`` DuckDB benchmark contract."""
    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
            f"ipfs_accelerate root not found: {root_path}"
        )

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
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
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
    _ensure_subset(
        "ipfs_accelerate time-series schema",
        REQUIRED_TIME_SERIES_TABLES,
        discovered_tables,
    )

    benchmark_schema_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    benchmark_schema_functions = tuple(
        sorted(set(re.findall(r"^def\s+([A-Za-z0-9_]+)\s*\(", benchmark_schema_source, flags=re.MULTILINE)))
    )
    _ensure_subset(
        "ipfs_accelerate create_benchmark_schema.py",
        REQUIRED_BENCHMARK_SCHEMA_FUNCTIONS,
        benchmark_schema_functions,
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
    _ensure_subset(
        "ipfs_accelerate schema-check utilities",
        REQUIRED_CHECK_SCHEMA_FUNCTIONS,
        check_schema_functions,
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


def discover_meta_wearables_dat_android_contract(
    root: str | Path,
) -> MetaWearablesDatAndroidContract:
    """Discover and validate the Android DAT display-access contract."""
    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
            f"meta-wearables-dat-android root not found: {root_path}"
        )

    contract_paths = tuple(root_path / rel for rel in REQUIRED_DAT_ANDROID_CONTRACT_PATHS)
    missing = [str(path) for path in contract_paths if not path.exists()]
    if missing:
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
            f"DAT Android display-access contract files missing: {missing}"
        )

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in contract_paths)
    _ensure_source_terms(
        "DAT Android DisplayAccess sample",
        combined_source,
        (
            "mwdat-display",
            "addDisplay",
            "sendContent",
            "DisplayState.STARTED",
            "DeviceSessionError.DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED",
        ),
    )

    schema_refs = {
        "time_series_schema": "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "benchmark_schema_script": (
            "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py"
        ),
        "check_database_schema": (
            "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py"
        ),
        "check_db_schema": "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    }

    return MetaWearablesDatAndroidContract(
        root=str(root_path),
        descriptor_paths=tuple(str(path) for path in contract_paths),
        contract_id="external.meta-wearables-dat-android.ipfs-accelerate-benchmark-widget@1",
        interface_contract=INTERFACE_CONTRACT,
        task_id=TASK_ID,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        goal_packet_goals=GOAL_PACKET_GOALS,
        producer="external/ipfs_accelerate",
        consumer="external/meta-wearables-dat-android",
        dat_display_methods=tuple(sorted(REQUIRED_DAT_ANDROID_METHODS)),
        table_by_method=dict(DAT_ANDROID_TABLE_BY_METHOD),
        schema_refs=schema_refs,
    )


def build_meta_wearables_dat_android_ipfs_accelerate_handoff(
    meta_wearables_dat_android_root: str | Path,
    ipfs_accelerate_root: str | Path,
    *,
    capability: str = "dat.android.display.performance_benchmark",
    payload: bytes | str | dict[str, Any] | None = None,
) -> MetaWearablesDatAndroidIPFSAccelerateHandoff:
    """Build a deterministic ``external/ipfs_accelerate`` to Android DAT handoff receipt."""
    dat_contract = discover_meta_wearables_dat_android_contract(meta_wearables_dat_android_root)
    duckdb_contract = discover_ipfs_accelerate_duckdb_contract(ipfs_accelerate_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "external/ipfs_accelerate",
            "target": "external/meta-wearables-dat-android",
            "capability": capability,
            "route": "ipfs-accelerate-benchmark-to-meta-wearables-dat-android",
            "time_series_tables": list(duckdb_contract.time_series_tables),
            "dat_display_methods": list(dat_contract.dat_display_methods),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return MetaWearablesDatAndroidIPFSAccelerateHandoff(
        contract_id=dat_contract.contract_id,
        source_repository="external/ipfs_accelerate",
        target_repository="external/meta-wearables-dat-android",
        interface_contract=INTERFACE_CONTRACT,
        task_id=TASK_ID,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        goal_packet_goals=GOAL_PACKET_GOALS,
        capability=capability,
        route="ipfs-accelerate-benchmark-to-meta-wearables-dat-android",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        time_series_tables=duckdb_contract.time_series_tables,
        dat_display_methods=dat_contract.dat_display_methods,
        table_by_method=dat_contract.table_by_method,
        benchmark_schema_functions=duckdb_contract.benchmark_schema_functions,
        check_schema_functions=duckdb_contract.check_schema_functions,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _ensure_subset(label: str, required: tuple[str, ...], observed: Any) -> None:
    missing = set(required) - set(observed)
    if missing:
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
            f"{label} missing required values: {sorted(missing)}"
        )


def _ensure_source_terms(label: str, source: str, required: tuple[str, ...]) -> None:
    missing = [term for term in required if term not in source]
    if missing:
        raise MetaWearablesDatAndroidIPFSAccelerateInteropError(
            f"{label} missing required source terms: {missing}"
        )
