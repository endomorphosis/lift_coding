"""Integration proof for VAIOS-G707 hallucinate_app <-> mobile interop.

This is a hardware-free objective validation repair gate.  It proves the
Hallucinate App dashboard, mobile ORB bridge, documentation, and DuckDB receipt
schema use the same handoff contract.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEARCH_INTERFACE = (
    REPO_ROOT
    / "hallucinate_app"
    / "hallucinate_app"
    / "node"
    / "dashboard"
    / "content_browser"
    / "search_interface.js"
)
TEST_INTERFACE = (
    REPO_ROOT
    / "hallucinate_app"
    / "hallucinate_app"
    / "node"
    / "views"
    / "test_interface.html"
)
MOBILE_ORB_BRIDGE = REPO_ROOT / "mobile" / "src" / "orb" / "metaGlassesMobileOrbBridge.js"
MOBILE_DISPLAY_CONTRACT = (
    REPO_ROOT / "mobile" / "src" / "utils" / "metaWearablesDatDisplayWidgetContract.js"
)
TIME_SERIES_SCHEMA = (
    REPO_ROOT
    / "hallucinate_app"
    / "ipfs_accelerate_py"
    / "data"
    / "duckdb"
    / "db_schema"
    / "time_series_schema.sql"
)
CREATE_SCHEMA_SCRIPT = (
    REPO_ROOT
    / "hallucinate_app"
    / "ipfs_accelerate_py"
    / "data"
    / "duckdb"
    / "scripts"
    / "create_benchmark_schema.py"
)
DOC = REPO_ROOT / "docs" / "integration" / "hallucinate_app-mobile.md"
DISCOVERY = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-07-08-mgw-579-objective-validation-repair.md"
)

HANDOFF_CONTRACT = "handsfree.hallucinate-app/mobile-search-handoff@0.1.0"
CONTROL_SURFACE_REF = "control_surface_contract:hallucinate-app:remote-client"
DIAGNOSTICS_CONTRACT = "handsfree.meta-glasses/mobile-orb-diagnostics@0.1.0"
DISPLAY_ACTION_CONTRACT = "handsfree.meta-glasses/display-widget-action@0.1.0"
RECEIPT_TABLE = "hallucinate_mobile_handoff_receipts"
HANDOFF_EVENT = "hallucinate-app:mobile-search-handoff"
DISPLAY_ACTION_IDS = [
    "mobile_render_display_widget",
    "mobile_update_display_widget",
    "mobile_clear_display_widget",
    "mobile_focus_display_widget",
    "mobile_activate_display_widget_action",
    "mobile_reset_display_widget_session",
    "mobile_play_display_widget_video",
    "mobile_subscribe_display_widget_updates",
]
DISPLAY_ORB_OPERATIONS = [
    "render_widget",
    "update_widget",
    "clear_widget",
    "focus_next",
    "activate",
    "reset_session",
    "play_video",
    "subscribe_updates",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_create_schema_module():
    spec = importlib.util.spec_from_file_location(
        "create_benchmark_schema", CREATE_SCHEMA_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dashboard_search_interface_exports_mobile_handoff_contract():
    source = read(SEARCH_INTERFACE)

    required_terms = [
        "HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT",
        "buildHallucinateAppMobileSearchHandoff",
        "getMobileInteropDescriptor",
        "buildMobileSearchHandoff",
        HANDOFF_CONTRACT,
        CONTROL_SURFACE_REF,
        DIAGNOSTICS_CONTRACT,
        DISPLAY_ACTION_CONTRACT,
        HANDOFF_EVENT,
        RECEIPT_TABLE,
        "hallucinate_app.content_browser.search_interface",
        "mobile.meta_glasses.mobile_orb_bridge",
        "mobile-search-handoff",
    ]
    for term in required_terms:
        assert term in source

    for field in (
        "contract",
        "control_surface_contract_ref",
        "correlation_id",
        "query",
        "filter",
        "mobile_operation",
        "orb_receipt_cid",
        "mediation_receipt",
    ):
        assert f"'{field}'" in source


def test_hallucinate_test_interface_advertises_same_mobile_contract():
    source = read(TEST_INTERFACE)

    assert 'data-hallucinate-mobile-interop-contract="' + HANDOFF_CONTRACT + '"' in source
    assert 'data-control-surface-contract-ref="' + CONTROL_SURFACE_REF + '"' in source
    assert HANDOFF_EVENT in source
    assert RECEIPT_TABLE in source
    assert "window.HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT" in source


def test_mobile_orb_bridge_accepts_hallucinate_remote_client_contract():
    source = read(MOBILE_ORB_BRIDGE)
    display_contract_source = read(MOBILE_DISPLAY_CONTRACT)

    assert "HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT" in source
    assert HANDOFF_CONTRACT in source
    assert CONTROL_SURFACE_REF in source
    assert DIAGNOSTICS_CONTRACT in source
    assert "normalizeDisplayWidgetMobileAction" in source
    assert "buildMobileOrbControlSurfaceArtifacts" in source
    assert "mediation_receipt" in source
    assert "remote_client_policy_contract: false" in source

    for action_id in DISPLAY_ACTION_IDS:
        assert action_id in display_contract_source
    for operation in DISPLAY_ORB_OPERATIONS:
        assert operation in display_contract_source


def test_duckdb_schema_records_handoff_receipts(tmp_path):
    module = load_create_schema_module()
    db_path = tmp_path / "interop.duckdb"
    conn = module.connect_to_db(db_path)
    try:
        module.create_schema(conn, force=True)

        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        assert RECEIPT_TABLE in tables
        assert "integration_test_results" in tables
        assert "hallucinate_mobile_handoff_history" in tables

        integration_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info('integration_test_results')").fetchall()
        }
        for column in (
            "hallucinate_mobile_contract",
            "control_surface_contract_ref",
            "mobile_orb_operation",
            "mobile_orb_receipt_cid",
            "mobile_mediation_receipt",
        ):
            assert column in integration_columns

        receipt_columns = {
            row[1] for row in conn.execute(f"PRAGMA table_info('{RECEIPT_TABLE}')").fetchall()
        }
        for column in (
            "receipt_id",
            "contract",
            "control_surface_contract_ref",
            "source_surface",
            "target_surface",
            "handoff_event",
            "correlation_id",
            "query",
            "filter",
            "mobile_operation",
            "orb_receipt_cid",
            "mediation_receipt",
            "diagnostics_contract",
        ):
            assert column in receipt_columns

        conn.execute(
            """
            INSERT INTO test_runs
            (run_id, test_name, test_type, success)
            VALUES (1, 'hallucinate_app_mobile_interop', 'integration', true)
            """
        )
        conn.execute(
            """
            INSERT INTO integration_test_results
            (test_result_id, run_id, test_module, test_name, status,
             hallucinate_mobile_contract, control_surface_contract_ref,
             mobile_orb_operation, mobile_orb_receipt_cid, mobile_mediation_receipt)
            VALUES (1, 1, 'test_hallucinate_app_mobile_interop',
                    'test_duckdb_schema_records_handoff_receipts', 'pass',
                    ?, ?, 'render_widget', 'sha256:orb-receipt', ?)
            """,
            [
                HANDOFF_CONTRACT,
                CONTROL_SURFACE_REF,
                json.dumps({"receipt_id": "sha256:mediation-receipt"}),
            ],
        )
        conn.execute(
            f"""
            INSERT INTO {RECEIPT_TABLE}
            (receipt_id, run_id, test_result_id, source_surface, target_surface,
             correlation_id, query, filter, mobile_operation, orb_receipt_cid,
             mediation_receipt)
            VALUES ('sha256:handoff-receipt', 1, 1,
                    'hallucinate_app.content_browser.search_interface',
                    'mobile.meta_glasses.mobile_orb_bridge',
                    'corr-vaios-g707', 'cid:demo', ?, 'render_widget',
                    'sha256:orb-receipt', ?)
            """,
            [
                json.dumps({"mimetype": "application/json"}),
                json.dumps({"receipt_id": "sha256:mediation-receipt"}),
            ],
        )
        row = conn.execute(
            f"""
            SELECT contract, control_surface_contract_ref, handoff_event,
                   mobile_operation, diagnostics_contract
            FROM {RECEIPT_TABLE}
            WHERE receipt_id = 'sha256:handoff-receipt'
            """
        ).fetchone()
        assert row == (
            HANDOFF_CONTRACT,
            CONTROL_SURFACE_REF,
            HANDOFF_EVENT,
            "render_widget",
            DIAGNOSTICS_CONTRACT,
        )
    finally:
        conn.close()


def test_sql_doc_and_discovery_keep_objective_repair_aligned():
    sql = read(TIME_SERIES_SCHEMA)
    doc = read(DOC)
    discovery = read(DISCOVERY)

    for source in (sql, doc, discovery):
        assert HANDOFF_CONTRACT in source
        assert CONTROL_SURFACE_REF in source
        assert RECEIPT_TABLE in source

    assert "objective validation repair" in discovery
    assert "VAIOS-G707" in discovery
    assert "tests/integration/test_hallucinate_app_mobile_interop.py" in discovery
    assert re.search(r"non-skipped\s+validation gate", doc)
