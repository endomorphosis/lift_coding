"""HAO-737 packet proof for Meta Wearables DAT Android and ipfs_accelerate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META_ROOT = ROOT / "external" / "meta-wearables-dat-android"
ACCEL_ROOT = ROOT / "external" / "ipfs_accelerate"
sys.path.insert(0, str(META_ROOT / "python"))

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_accelerate"


def test_meta_android_events_project_to_accelerate_time_series_metrics():
    from meta_wearables_dat_android.ipfs_kit_handoff import build_ipfs_kit_handoff

    event = {
        "device_id": "android-dat-glasses-01",
        "event_type": "inference_latency_sample",
        "sequence": 737,
        "captured_at": "2026-07-08T00:00:00Z",
        "payload": {
            "model_name": "display-widget-renderer",
            "hardware_type": "android_dat_glasses",
            "latency_ms": 18.5,
            "memory_mb": 42,
            "power_watts": 1.7,
        },
    }
    envelope = build_ipfs_kit_handoff(event, request_id="hao-737", pin=False)
    metrics = envelope["payload"]["payload"]

    assert envelope["producer"] == "external/meta-wearables-dat-android"
    assert metrics["latency_ms"] > 0
    assert {"model_name", "hardware_type", "latency_ms", "memory_mb", "power_watts"}.issubset(metrics)


def test_accelerate_interface_descriptors_cover_wearable_metric_columns():
    schema = (ACCEL_ROOT / "data" / "duckdb" / "db_schema" / "time_series_schema.sql").read_text()
    for token in (
        "performance_results",
        "hardware_platforms",
        "latency_ms",
        "memory_mb",
        "power_watts",
        "run_group_id",
    ):
        assert token in schema

    for relative in (
        "data/duckdb/scripts/create_benchmark_schema.py",
        "data/duckdb/utils/check_database_schema.py",
        "data/duckdb/utils/check_db_schema.py",
        "data/duckdb/utils/implement_db_schema_enhancements.py",
        "data/duckdb/utils/onnx_db_schema_update.py",
    ):
        assert (ACCEL_ROOT / relative).exists(), relative


def test_accelerate_doc_records_objective_validation_repair():
    doc = (
        ROOT
        / "docs"
        / "integration"
        / "external_meta_wearables_dat_android-external_ipfs_accelerate.md"
    ).read_text()
    assert INTERFACE_CONTRACT in doc
    assert "objective validation repair" in doc
    assert "VAIOS-G709" in doc
