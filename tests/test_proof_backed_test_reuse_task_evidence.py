from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task_evidence", ROOT / "scripts/proof_backed_test_reuse_task_evidence.py")
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evidence
SPEC.loader.exec_module(evidence)


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"; root.mkdir()
    for args in (("git", "init", "-q"), ("git", "config", "user.email", "test@example.invalid"), ("git", "config", "user.name", "test")):
        subprocess.run(args, cwd=root, check=True)
    (root / "owned.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=root, check=True); subprocess.run(("git", "commit", "-qm", "base"), cwd=root, check=True)
    return root


def manifest(path: Path, *, bad: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"")
    value = {"schema": evidence.EVENT_MANIFEST_SCHEMA, "generation": 0, "active_path": path.name, "stream_id": "stream", "snapshot_id": "snapshot", "earliest_sequence": 1, "latest_sequence": 0, "last_event_id": "", "active_indexed_bytes": 0, "files": [{"path": path.name, "size_bytes": 0, "event_count": 0, "first_sequence": 1, "last_sequence": 0, "start_previous_event_id": "", "sha256": "", "canonical_events": True}]}
    value["manifest_digest"] = "broken" if bad else evidence.sha256(value)
    path.with_suffix(path.suffix + ".manifest.json").write_text(json.dumps(value), encoding="utf-8")


def roots(tmp_path: Path, *, bad: bool = False) -> Path:
    v8 = tmp_path / "proof-backed-test-reuse-v8"
    for version in ("v8", "v6", "v1"):
        root = tmp_path / f"proof-backed-test-reuse-{version}"
        for lane in evidence.LANES:
            manifest(root / "state" / f"ptr_lane_{lane}" / f"ptr_lane_{lane}_events.jsonl", bad=bad and version == "v1" and lane == 0)
    return v8


def task(status: str = "completed") -> evidence.TaskIdentity:
    return evidence.TaskIdentity("PTR-011", "task/v1/key", "baguqeeratask", "G-011", status, ("owned.py",), ("pytest owned.py",))


def board(status: str = "completed") -> evidence.Board:
    item = task(status)
    return evidence.Board({item.task_id: item}, {"missing-later.py": "PTR-011"})


def test_report_cid_is_deterministic_and_existing_file_is_rehashed(tmp_path: Path) -> None:
    report = {"schema": evidence.REPORT_SCHEMA, "audit_valid": True, "ready": False, "gaps": []}
    report["report_cid"] = evidence.canonical_cid(report)
    path = evidence.write_report(report, tmp_path)
    assert evidence.write_report(report, tmp_path) == path
    path.write_text("tampered", encoding="utf-8")
    try:
        evidence.write_report(report, tmp_path)
    except RuntimeError as exc:
        assert "different bytes" in str(exc)
    else: assert False


def test_configured_root_is_complete_override(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("IPFS_PROOF_REUSE_STATE_ROOT", str(tmp_path / "chosen"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "ignored"))
    assert evidence.configured_root() == tmp_path / "chosen"


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    root = roots(tmp_path, bad=True)
    report = evidence.ProofReuseTaskEvidenceValidator(state_root=root, repo_root=repo(tmp_path), now_ms=1, board_loader=board).audit()
    assert not report["audit_valid"]
    assert any(item.startswith("EVENT_MANIFEST_INVALID:v1:0") for item in report["audit_errors"])


def test_flat_validation_receipt_rejects_body_and_command_tampering(tmp_path: Path) -> None:
    root, checkout = roots(tmp_path), repo(tmp_path)
    validator = evidence.ProofReuseTaskEvidenceValidator(state_root=root, repo_root=checkout, now_ms=1, board_loader=board)
    item, snapshot = task(), validator.snapshot
    receipt = {"schema": evidence.RECEIPT_SCHEMA, "task_id": item.task_id, "task_cid": item.canonical_task_cid, "goal_id": item.goal_id, "validation_command": item.validation[0], "validation_command_cid": evidence.canonical_cid({"command": item.validation[0]}), "proof_reuse_mode": "off", "disposition": "executed", "passed": True, "status": "passed", "exit_code": 0, "skipped_count": 0, "repository_id": snapshot.repository_id, "repository_state_cid": snapshot.repository_state_cid, "git_commit_id": snapshot.commit, "git_tree_id": snapshot.tree, "gitlink_state_cid": snapshot.gitlink_state_cid, "repository_forest_cid": snapshot.repository_forest_cid, "dirty": snapshot.dirty, "dirty_overlay_cid": snapshot.dirty_overlay_cid, "observed_at_ms": 1, "fresh_until_ms": 2}
    receipt["validation_receipt_cid"] = evidence.canonical_cid(receipt)
    path = root.parent / "proof-backed-test-reuse-v1/projection/completion/validation_receipts/PTR-011.json"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validator._validation(item, root.parent / "proof-backed-test-reuse-v1") == (True, "")
    receipt["validation_command_cid"] = "wrong"; path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validator._validation(item, root.parent / "proof-backed-test-reuse-v1")[1] == "VALIDATION_RECEIPT_BODY_CID_MISMATCH"


def test_incomplete_audit_has_owner_attributed_gap_and_no_paths_in_report(tmp_path: Path) -> None:
    root = roots(tmp_path); report = evidence.ProofReuseTaskEvidenceValidator(state_root=root, repo_root=repo(tmp_path), now_ms=1, board_loader=board).audit()
    assert report["audit_valid"] and not report["ready"]
    assert {gap["kind"] for gap in report["gaps"]} >= {"COMPLETION_PROVENANCE_GAP", "VALIDATION_RECEIPT_MISSING", "PENDING_LATER_OWNER"}
    assert str(tmp_path) not in evidence.canonical_json(report).decode()
