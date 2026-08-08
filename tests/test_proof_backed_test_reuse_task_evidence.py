from __future__ import annotations

import importlib.util
import json
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


def write_board(tmp_path: Path, *, status: str = "completed") -> Path:
    board = tmp_path / "board.md"
    board.write_text(
        "## PTR-001 First\n\n- Status: completed\n- Depends on:\n- Goal id: G1\n"
        "- Outputs: scripts/owned.py\n- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q\n\n"
        f"## PTR-002 Second\n\n- Status: {status}\n- Depends on: PTR-001\n- Goal id: G2\n"
        "- Outputs: scripts/owned.py\n- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q\n",
        encoding="utf-8",
    )
    return board


def receipt(task_id: str, snapshot: object, command: str, *, commit: str | None = None, fresh: int = 9_999_999_999_999) -> dict[str, object]:
    return {
        "task_id": task_id,
        "merge_receipt_cid": "baguqeera" + task_id.lower(),
        "git_commit_id": commit or snapshot.commit,
        "validation_receipt_cid": "baguqeeravalid" + task_id.lower(),
        "validation_command": command,
        "passed": True,
        "proof_reuse_mode": "off",
        "fresh_until_ms": fresh,
        "git_tree_id": snapshot.tree,
        "gitlink_state_cid": snapshot.gitlink_state_cid,
    }


def write_receipts(root: Path, values: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index, value in enumerate(values):
        (root / f"receipt-{index}.json").write_text(json.dumps(value), encoding="utf-8")


def test_canonical_cid_is_stable_and_report_write_is_idempotent(tmp_path: Path) -> None:
    assert evidence.canonical_cid({"b": 2, "a": 1}) == evidence.canonical_cid({"a": 1, "b": 2})
    report = {"schema": evidence.REPORT_SCHEMA}
    report["report_cid"] = evidence.canonical_cid(report)
    first = evidence.write_report(report, tmp_path)
    assert first == evidence.write_report(report, tmp_path)
    assert first.name == f"{report['report_cid']}.json"
    persisted = json.loads(first.read_text(encoding="utf-8"))
    claimed = persisted.pop("report_cid")
    assert claimed == evidence.canonical_cid(persisted)


def test_live_audit_requires_files_ancestor_receipts_and_fresh_exact_validation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path)
    state = tmp_path / "state"
    validator = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100)
    missing = validator.audit()
    kinds = {gap["kind"] for gap in missing["gaps"]}
    assert not missing["ready"]
    assert {"COMPLETION_RECEIPT_MISSING", "VALIDATION_RECEIPT_MISSING", "DEPENDENCY_OWNERSHIP_UNPROVEN"} <= kinds

    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    write_receipts(state, [receipt("PTR-001", snapshot, command), receipt("PTR-002", snapshot, command)])
    ready = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert ready["ready"]
    assert ready["dependency_order"] == [{"later_task": "PTR-002", "dependency": "PTR-001", "later_commit": snapshot.commit, "dependency_commit": snapshot.commit, "ordered": True}]


@pytest.mark.parametrize("mutation, expected", [
    (lambda value, snapshot: value.update({"fresh_until_ms": 99}), "VALIDATION_RECEIPT_STALE"),
    (lambda value, snapshot: value.update({"git_tree_id": "0" * 40}), "VALIDATION_PIN_MISMATCH"),
    (lambda value, snapshot: value.update({"validation_command": "pytest wrong.py"}), "VALIDATION_COMMAND_MISMATCH"),
])
def test_invalid_validation_evidence_is_never_ready(tmp_path: Path, mutation: object, expected: str) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    value = receipt("PTR-001", snapshot, command)
    mutation(value, snapshot)
    state = tmp_path / "state"
    write_receipts(state, [value])
    report = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert not report["ready"]
    assert expected in {gap["kind"] for gap in report["gaps"]}


def test_non_ancestor_receipt_and_wrong_submodule_pin_are_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    snapshot = evidence.GitSnapshot(repo)
    command = "IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_owned.py -q"
    subprocess.run(("git", "checkout", "-qb", "side"), cwd=repo, check=True)
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    subprocess.run(("git", "add", "side.txt"), cwd=repo, check=True)
    subprocess.run(("git", "commit", "-qm", "side"), cwd=repo, check=True)
    side = git(repo, "rev-parse", "HEAD")
    subprocess.run(("git", "checkout", "-q", "master"), cwd=repo, check=True)
    state = tmp_path / "state"
    write_receipts(state, [receipt("PTR-001", snapshot, command, commit=side)])
    report = evidence.ProofReuseTaskEvidenceValidator(board, state, repo, now_ms=100).audit()
    assert "RECEIPT_COMMIT_NOT_ANCESTOR" in {gap["kind"] for gap in report["gaps"]}


def test_wrong_gitlink_pin_is_not_treated_as_a_present_output(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    board = write_board(tmp_path, status="todo")
    validator = evidence.ProofReuseTaskEvidenceValidator(board, tmp_path / "state", repo, now_ms=100)
    # Model a checked-out component whose observed pin cannot equal the board's
    # expected live gitlink.  The validator must report the pin mismatch rather
    # than accepting the working-tree file.
    validator.snapshot.gitlinks["scripts"] = "0" * 40
    report = validator.audit()
    assert "GITLINK_PIN_MISMATCH" in {gap["kind"] for gap in report["gaps"]}
