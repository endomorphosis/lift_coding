"""Interop contract between ``hallucinate_app`` and the mobile client.

MGW-579 repairs VAIOS-G707 by making the Hallucinate App content browser
handoff to mobile explicit and testable. The Hallucinate App submodule has a
mix of JavaScript UI descriptors and DuckDB benchmark schema files, so this
module discovers those assets statically instead of importing submodule code.
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
EVENT_NAME = "hallucinate-app:mobile-interop-handoff"
ROUTE = "hallucinate-app-content-browser-to-mobile-widget"

REQUIRED_CONTENT_BROWSER_OPERATIONS = (
    "search_content_index",
    "apply_content_filter",
    "clear_content_search",
    "save_content_search",
    "select_saved_search",
    "refresh_search_suggestions",
)

REQUIRED_MOBILE_WIDGET_ACTIONS = (
    "mobile_render_search_results_widget",
    "mobile_update_search_filter_widget",
    "mobile_clear_search_results_widget",
    "mobile_open_content_item",
)

REQUIRED_TIME_SERIES_TABLES = (
    "hallucinate_app_mobile_interop_events",
    "performance_baselines",
    "performance_regressions",
    "performance_trends",
    "regression_notifications",
)


class HallucinateAppMobileInteropError(RuntimeError):
    """Raised when either side of the Hallucinate App/mobile contract is missing."""


@dataclass(frozen=True)
class HallucinateAppMobileContract:
    """Static contract discovered from the Hallucinate App and mobile surfaces."""

    root: str
    search_interface_path: str
    test_interface_path: str
    time_series_schema_path: str
    benchmark_schema_script_path: str
    content_browser_operations: tuple[str, ...]
    mobile_widget_actions: tuple[str, ...]
    html_fixture_ids: tuple[str, ...]
    time_series_tables: tuple[str, ...]
    benchmark_schema_functions: tuple[str, ...]


@dataclass(frozen=True)
class HallucinateAppMobileHandoff:
    """Deterministic receipt for one Hallucinate App payload routed to mobile."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    event_name: str
    route: str
    endpoint_path: str
    method: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    content_browser_operations: tuple[str, ...]
    required_mobile_widget_actions: tuple[str, ...]
    time_series_tables: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_hallucinate_app_mobile_contract(
    root: str | Path,
) -> HallucinateAppMobileContract:
    """Discover the Hallucinate App/mobile interop descriptor assets."""
    root_path = Path(root)
    if not root_path.exists():
        raise HallucinateAppMobileInteropError(
            f"hallucinate_app root not found: {root_path}"
        )

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
            f"Hallucinate App/mobile descriptor assets missing: {missing}"
        )

    search_source = search_interface_path.read_text(encoding="utf-8")
    missing_operations = [
        operation
        for operation in REQUIRED_CONTENT_BROWSER_OPERATIONS
        if operation not in search_source
    ]
    if missing_operations:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js is missing operations: {missing_operations}"
        )
    missing_actions = [
        action for action in REQUIRED_MOBILE_WIDGET_ACTIONS if action not in search_source
    ]
    if missing_actions:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js is missing mobile widget actions: {missing_actions}"
        )
    if EVENT_NAME not in search_source:
        raise HallucinateAppMobileInteropError(
            f"search_interface.js is missing {EVENT_NAME}"
        )

    html_source = test_interface_path.read_text(encoding="utf-8")
    fixture_ids = tuple(
        sorted(set(re.findall(r'id="([^"]*hallucinate-app-mobile-interop[^"]*)"', html_source)))
    )
    if "hallucinate-app-mobile-interop-fixture" not in fixture_ids:
        raise HallucinateAppMobileInteropError(
            "test_interface.html is missing hallucinate-app-mobile-interop-fixture"
        )

    schema_sql = time_series_schema_path.read_text(encoding="utf-8")
    time_series_tables = tuple(
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
    missing_tables = set(REQUIRED_TIME_SERIES_TABLES) - set(time_series_tables)
    if missing_tables:
        raise HallucinateAppMobileInteropError(
            f"time_series_schema.sql is missing tables: {sorted(missing_tables)}"
        )

    benchmark_source = benchmark_schema_script_path.read_text(encoding="utf-8")
    benchmark_schema_functions = tuple(
        sorted(set(re.findall(r"def\s+([A-Za-z0-9_]+)", benchmark_source)))
    )
    required_functions = {
        "create_performance_tables",
        "create_hallucinate_app_mobile_interop_tables",
    }
    missing_functions = required_functions - set(benchmark_schema_functions)
    if missing_functions:
        raise HallucinateAppMobileInteropError(
            f"create_benchmark_schema.py is missing functions: {sorted(missing_functions)}"
        )

    return HallucinateAppMobileContract(
        root=str(root_path),
        search_interface_path=str(search_interface_path),
        test_interface_path=str(test_interface_path),
        time_series_schema_path=str(time_series_schema_path),
        benchmark_schema_script_path=str(benchmark_schema_script_path),
        content_browser_operations=REQUIRED_CONTENT_BROWSER_OPERATIONS,
        mobile_widget_actions=REQUIRED_MOBILE_WIDGET_ACTIONS,
        html_fixture_ids=fixture_ids,
        time_series_tables=time_series_tables,
        benchmark_schema_functions=benchmark_schema_functions,
    )


def build_hallucinate_app_mobile_handoff(
    hallucinate_app_root: str | Path,
    *,
    payload: bytes | str | dict[str, Any] | None = None,
) -> HallucinateAppMobileHandoff:
    """Build a deterministic Hallucinate App to mobile handoff receipt."""
    contract = discover_hallucinate_app_mobile_contract(hallucinate_app_root)
    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "hallucinate_app",
            "target": "mobile",
            "event_name": EVENT_NAME,
            "route": ROUTE,
            "content_browser_operations": list(contract.content_browser_operations),
            "mobile_widget_actions": list(contract.mobile_widget_actions),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return HallucinateAppMobileHandoff(
        contract_id="handsfree.hallucinate-app.mobile@1",
        source_repository="hallucinate_app",
        target_repository="mobile",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        event_name=EVENT_NAME,
        route=ROUTE,
        endpoint_path="/v1/hallucinate-app/content-browser/search",
        method="POST",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        content_browser_operations=contract.content_browser_operations,
        required_mobile_widget_actions=contract.mobile_widget_actions,
        time_series_tables=tuple(
            table
            for table in contract.time_series_tables
            if table in REQUIRED_TIME_SERIES_TABLES
        ),
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
