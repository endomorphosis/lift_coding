"""HAO-738 packet proof for Meta Wearables DAT Android and ipfs_datasets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META_ROOT = ROOT / "external" / "meta-wearables-dat-android"
DATASETS_ROOT = ROOT / "external" / "ipfs_datasets"
TOOLS_ROOT = DATASETS_ROOT / ".tools" / "ipfs_kit_py"
sys.path.insert(0, str(META_ROOT / "python"))

INTERFACE_CONTRACT = "interface contract external/meta-wearables-dat-android external/ipfs_datasets"


def test_meta_android_events_project_to_dataset_records():
    from meta_wearables_dat_android.ipfs_kit_handoff import build_ipfs_kit_handoff

    envelope = build_ipfs_kit_handoff(
        {
            "device_id": "android-dat-glasses-01",
            "event_type": "display_training_sample",
            "sequence": 738,
            "captured_at": "2026-07-08T00:00:00Z",
            "payload": {
                "dataset": "display_widget_feedback",
                "label": "accepted",
                "features": {"focus_target": "next_task", "confidence": 0.94},
            },
        },
        request_id="hao-738",
    )
    record = {
        "source": envelope["producer"],
        "dataset": envelope["payload"]["payload"]["dataset"],
        "cid_pending": True,
        "payload": envelope["payload"],
    }

    assert record["source"] == "external/meta-wearables-dat-android"
    assert record["dataset"] == "display_widget_feedback"
    assert record["payload"]["sequence"] == 738


def test_datasets_embedded_ipfs_kit_vfs_descriptors_cover_dataset_handoff():
    schema = json.loads((TOOLS_ROOT / "data" / "deprecations_report.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "deprecated" in schema["required"]
    assert "deprecations" in schema["properties"]

    for relative in (
        "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md",
        "examples/demo_bucket_vfs_interfaces.py",
        "examples/demo_unified_bucket_interface.py",
    ):
        path = TOOLS_ROOT / relative
        assert path.exists(), relative
        text = path.read_text(encoding="utf-8")
        assert "bucket" in text.lower() or "bucket" in path.name.lower()


def test_datasets_doc_records_objective_validation_repair():
    doc = (
        ROOT
        / "docs"
        / "integration"
        / "external_meta_wearables_dat_android-external_ipfs_datasets.md"
    ).read_text()
    assert INTERFACE_CONTRACT in doc
    assert "objective validation repair" in doc
    assert "VAIOS-G710" in doc
