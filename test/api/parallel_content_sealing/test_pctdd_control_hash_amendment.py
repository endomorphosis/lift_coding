"""Reviewed source hash updates preserve historical task and source evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BASE = "3e6a1829cd8273566a88e179b88636e3517da380"
APPROVED = {
    "config/parallel_content_sealing_proof_carrying_tdd_ensure.timer",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_user_systemd.py",
    "test/api/parallel_content_sealing/test_pctdd_user_systemd_ensure.py",
}
MANIFEST = "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
SEAL = "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
HASHES = "protected_control_hashes_before_manifest_and_seal"


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        "pctdd_source_hash_fixture", ROOT / "scripts" / name
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def old(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path])


def test_pure_current_manifest_changes_only_reviewed_source_hashes():
    module = load_script("generate_parallel_content_sealing_proof_carrying_tdd_controls.py")
    before = json.loads(old(MANIFEST))
    after = json.loads((ROOT / MANIFEST).read_bytes())
    assert after == module.render_control_manifest()
    assert {k: v for k, v in after.items() if k != HASHES} == {
        k: v for k, v in before.items() if k != HASHES
    }
    assert after.keys() == before.keys()
    assert after[HASHES].keys() == before[HASHES].keys()
    assert {k for k, v in after[HASHES].items() if v != before[HASHES][k]} == APPROVED
    assert after["historical_completion_reissued"] is False
    assert after["manifest_is_completion_receipt"] is False


def test_seal_changes_only_reviewed_hashes_and_transitive_manifest_hash():
    before = json.loads(old(SEAL))
    after = json.loads((ROOT / SEAL).read_bytes())
    assert before.keys() == after.keys()
    assert {k: v for k, v in before.items() if k != "artifacts"} == {
        k: v for k, v in after.items() if k != "artifacts"
    }
    assert before["artifacts"].keys() == after["artifacts"].keys()
    assert {k for k, v in after["artifacts"].items() if v != before["artifacts"][k]} == APPROVED | {
        MANIFEST
    }
    for relative in APPROVED | {MANIFEST}:
        assert (
            after["artifacts"][relative]
            == "sha256:" + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        )


def test_all_other_protected_artifacts_and_completion_receipts_are_unchanged():
    manifest = json.loads(old(MANIFEST))
    for relative in manifest[HASHES]:
        if relative not in APPROVED:
            assert (ROOT / relative).read_bytes() == old(relative), relative
    for relative in subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-tree",
            "-r",
            "--name-only",
            BASE,
            "--",
            "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts",
        ],
        text=True,
    ).splitlines():
        assert (ROOT / relative).read_bytes() == old(relative), relative


@pytest.mark.parametrize("relative", sorted(APPROVED))
def test_actual_board_validator_still_rejects_each_unmatched_source_hash(monkeypatch, relative):
    module = load_script("validate_parallel_content_sealing_proof_carrying_tdd_board.py")
    actual_load = module._load_json

    def mismatched(path):
        value = actual_load(path)
        if path == module.CONTROL_MANIFEST_PATH:
            value[HASHES][relative] = "sha256:" + "0" * 64
        return value

    monkeypatch.setattr(module, "_load_json", mismatched)
    report = module.validate()
    assert report["valid"] is False
    assert "PCTDD-000 control manifest hash differs: " + relative in report["errors"]
