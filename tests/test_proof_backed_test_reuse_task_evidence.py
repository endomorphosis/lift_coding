from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/proof_backed_test_reuse_task_evidence.py"
SPEC = importlib.util.spec_from_file_location("task_evidence", SCRIPT)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evidence
SPEC.loader.exec_module(evidence)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=root, text=True).strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(evidence.canonical_json(value))


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=repo, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=repo, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=repo, check=True)
    (repo / "scripts").mkdir()
    (repo / "tests").mkdir()
    (repo / "scripts" / "owned.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "tests" / "test_owned.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    subprocess.run(("git", "add", "."), cwd=repo, check=True)
    subprocess.run(("git", "commit", "-qm", "initial"), cwd=repo, check=True)
    return repo


COMMAND = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"


def write_board(tmp_path: Path, *, owner: bool = False) -> Path:
    output = "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py" if owner else "scripts/owned.py"
    board = tmp_path / "board.md"
    board.write_text(
        "## PTR-001 First\n\n- Status: completed\n- Depends on:\n- Goal id: G1\n"
        f"- Outputs: {output}\n- Validation: {COMMAND}\n\n"
        + ("## PTR-163 Later owner\n\n- Status: todo\n- Depends on: PTR-001\n- Goal id: G2\n"
           "- Outputs: scripts/future.py\n- Validation: python3 -m pytest tests/test_owned.py -q\n" if owner else ""),
        encoding="utf-8",
    )
    return board


def write_event_chain(state: Path, *, tamper: bool = False) -> None:
    lane = state / "state" / "ptr_lane_0"
    payload = {"previous_event_id": "", "kind": "reconciled", "request_id": "r1"}
    payload["event_id"] = evidence._sha256(evidence.canonical_json(payload))
    if tamper:
        payload["kind"] = "forged"
    events = lane / "ptr_lane_0_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    write_json(lane / "ptr_lane_0_events.jsonl.manifest.json", {
        "schema": evidence.EVENT_MANIFEST_SCHEMA,
        "files": [{"path": events.name, "canonical_events": True, "event_count": 1, "start_previous_event_id": ""}],
    })


def task(board: Path) -> object:
    return evidence.parse_board(board)["PTR-001"]


def write_authority(state: Path, task: object, snapshot: object, *, fresh: bool = True,
                    tamper_validation: bool = False, train_status: str = "merged") -> None:
    dedupe = "a" * 64
    request = "request-001"
    identity = {"task_id": task.task_id, "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid}
    queue = {"status": "completed", "request_id": request, "dedupe_key": dedupe, **identity,
             "canonical_task_id": task.canonical_task_cid,
             "metadata": {"schema": evidence.COMPLETION_SCHEMA, "task": identity,
                          "completion_task_cids": {task.task_id: task.canonical_task_cid}}}
    write_json(state / "merge-queue" / "completed" / "request-001.json", queue)
    train = {"status": train_status, "integrated": train_status in {"merged", "already_merged"},
             "request_id": request, "task_id": task.task_id,
             "canonical_task_id": task.canonical_task_key, "target_commit": snapshot.commit,
             "merge_result": {"integration_commit_proof": {"passed": True}}}
    write_json(state / "merge-queue" / "train" / "receipts" / f"{dedupe}.json", train)
    payload = {**identity, "validation_command_cid": evidence.canonical_validation_command_cid(task.validation_command),
               "proof_reuse_mode": "off", "passed": True, "exit_code": 0, "skipped": 0,
               "git_commit_id": snapshot.commit, "git_tree_id": snapshot.tree,
               "gitlink_state_cid": snapshot.gitlink_state_cid, "fresh": fresh}
    record = {"schema": "ipfs_accelerate_py/proof-reuse-validation-receipt@1",
              "validation_receipt_cid": evidence.canonical_cid(payload), "payload": payload}
    if tamper_validation:
        record["payload"]["passed"] = False
    receipt = state / "state" / "preflight" / "reconciliation" / "ptr_lane_0" / "validation" / "receipts"
    write_json(receipt / f"{evidence.canonical_cid(record)}.json", record)


def audit(repo: Path, board: Path, state: Path) -> dict[str, object]:
    return evidence.ProofReuseTaskEvidenceValidator(board, state, repo).audit()


def test_canonical_board_join_and_historical_receipts_make_a_ready_report(tmp_path: Path) -> None:
    repo, board, state = make_repo(tmp_path), write_board(tmp_path), tmp_path / "v8"
    snapshot = evidence.GitSnapshot(repo)
    write_event_chain(state)
    write_authority(state, task(board), snapshot)
    first, second = audit(repo, board, state), audit(repo, board, state)
    assert first == second
    assert first["audit_valid"] and first["ready"]
    assert first["tasks"][0]["identity"] == {"task_id": "PTR-001", "canonical_task_key": task(board).canonical_task_key,
                                                   "canonical_task_cid": task(board).canonical_task_cid}
    assert first["report_cid"] == evidence.canonical_cid({key: value for key, value in first.items() if key != "report_cid"})


@pytest.mark.parametrize(("fresh", "tamper", "expected"), [
    (False, False, "VALIDATION_RECEIPT_STALE"),
    (True, True, "VALIDATION_RECEIPT_UNAUTHENTICATED"),
])
def test_stale_or_forged_validation_is_a_typed_gap(tmp_path: Path, fresh: bool, tamper: bool, expected: str) -> None:
    repo, board, state = make_repo(tmp_path), write_board(tmp_path), tmp_path / "v8"
    write_event_chain(state)
    write_authority(state, task(board), evidence.GitSnapshot(repo), fresh=fresh, tamper_validation=tamper)
    report = audit(repo, board, state)
    assert report["audit_valid"] and not report["ready"]
    assert expected in {gap["kind"] for gap in report["gaps"]}


def test_failed_and_quarantined_rows_are_not_authority(tmp_path: Path) -> None:
    repo, board, state = make_repo(tmp_path), write_board(tmp_path), tmp_path / "v8"
    write_event_chain(state)
    rogue = {"status": "completed", "task_id": "PTR-001", "metadata": {"schema": evidence.COMPLETION_SCHEMA}}
    write_json(state / "merge-queue" / "failed" / "rogue.json", rogue)
    write_json(state / "quarantine" / "validation.json", rogue)
    report = audit(repo, board, state)
    assert report["audit_valid"] and "COMPLETION_RECEIPT_MISSING" in {gap["kind"] for gap in report["gaps"]}


def test_event_tamper_fails_closed_and_cid_named_report_is_rehashed(tmp_path: Path) -> None:
    repo, board, state = make_repo(tmp_path), write_board(tmp_path), tmp_path / "v8"
    write_event_chain(state, tamper=True)
    assert not audit(repo, board, state)["audit_valid"]
    report = {"schema": evidence.REPORT_SCHEMA}
    report["report_cid"] = evidence.canonical_cid(report)
    path = evidence.write_report(report, state)
    path.write_text("forged", encoding="utf-8")
    with pytest.raises(ValueError, match="does not rehash"):
        evidence.write_report(report, state)


def test_configured_root_and_ptr_163_owner_drive_expect_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "configured"
    state = base / evidence.SEALED_STATE_SUFFIX
    repo, board = make_repo(tmp_path), write_board(tmp_path, owner=True)
    write_event_chain(state)
    monkeypatch.setenv(evidence.STATE_ROOT_ENV, str(base))
    assert evidence.default_state_root() == state
    report = audit(repo, board, state)
    owner_gaps = [gap for gap in report["gaps"] if gap["owner_attributed"]]
    assert report["audit_valid"] and not report["ready"]
    assert owner_gaps and "PTR-163" in owner_gaps[0]["detail"]


def test_missing_state_and_malformed_board_fail_closed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = tmp_path / "broken.md"
    board.write_text("not a board", encoding="utf-8")
    report = audit(repo, board, tmp_path / "absent")
    assert not report["audit_valid"]
    assert {"STATE_ROOT_MISSING", "EVENT_CHAIN_MISSING"} <= set(report["audit_errors"])
